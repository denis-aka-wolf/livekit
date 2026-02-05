from __future__ import annotations

import asyncio
import logging
from typing import Any

from livekit import rtc, api
from livekit.agents import (
    AgentSession,
    Agent,
    JobContext,
    function_tool,
    RunContext,
    get_job_context,
    # RoomInputOptions,
    # RoomOptions,
)
from livekit.agents.llm import ChatMessage

logger = logging.getLogger("elaina-inbound-worker")
logger.setLevel(logging.INFO)


class InboundAgent(Agent):
    def __init__(self, *, phone_number: str = ""):
        # Словарь сопоставления номеров телефонов именам клиентов
        phone_to_name = {
            "79133888778": "Денис Сергеевич",
            "79955701443": "Денис",
            "79137296699": "Павел",
            "79831379240": "Артем"
        }
        # Определяем имя клиента по номеру телефона
        self.client_name = phone_to_name.get(phone_number, "Иван")
        
        # Загружаем промпт из внешнего обработчика
        from .prompt_processor import load_and_process_prompt
        prompt_template = load_and_process_prompt(phone_number, self.client_name)
        
        super().__init__(instructions=prompt_template)
        
        # keep reference to the participant for transfers
        self.participant: rtc.RemoteParticipant | None = None

        self.phone_number = phone_number
        
        # Флаг для отслеживания состояния завершения вызова
        self.call_ended = False
        
        # Список ключевых фраз прощания, которые должны приводить к завершению вызова
        self.farewell_phrases = [
            "спасибо за обращение",
            "хорошего дня",
            "до свидания",
            "всего доброго",
            "благодарю за звонок",
            "рада была помочь",
            "звоните еще",
            "обращайтесь еще",
            "спасибо, до свидания",
            "спасибо, хорошего дня",
            "ладно, до свидания",
            "всего наилучшего",
            "благодарю, до новых встреч",
            "рада была помочь, до свидания",
            "спасибо за обращение! до свидания",
            "хорошо, до связи",
            "пока",
            "покидаю вас",
            "завершаю вызов"
        ]

    def set_participant(self, participant: rtc.RemoteParticipant):
        self.participant = participant

    async def _trigger_end_call(self):
        """Инициирует завершение вызова с корректной синхронизацией"""
        if self.call_ended:
            logger.info("Вызов уже завершён, пропускаем дубликат")
            return

        logger.info(f"Начинаем завершение вызова для {self.participant.identity}")
        self.call_ended = True

        try:
            # Получаем контекст задания
            job_ctx = get_job_context()
            
            # Удаляем комнату для завершения вызова
            if job_ctx.room and hasattr(job_ctx.room, 'name'):
                logger.info(f"Пытаюсь удалить комнату: {job_ctx.room.name}")
                await job_ctx.api.room.delete_room(
                    api.DeleteRoomRequest(room=job_ctx.room.name)
                )
                logger.info("Комната удалена, вызов завершён")
            else:
                logger.warning("Комната недоступна для удаления")
                
        except Exception as e:
            logger.error(f"Ошибка при удалении комнаты: {e}")
            
            # Если удаление комнаты не удалось, пробуем альтернативные способы
            try:
                # Попробуем закрыть комнату через другие средства
                if hasattr(job_ctx, 'close'):
                    await job_ctx.close()
                    
            except Exception as e2:
                logger.error(f"Ошибка при альтернативном завершении вызова: {e2}")
                
        finally:
            logger.info(f"Завершение вызова для {self.participant.identity} завершено")

    async def hangup(self):
        """Завершение вызова с защитой от повторных вызовов"""
        await self._trigger_end_call()

    @function_tool()
    async def transfer_call(self, ctx: RunContext, transfer_to: str):
        """Перевести звонок оператору, после подтверждения пользователя."""

        if not transfer_to:
            return "cannot transfer call"

        logger.info(f"transferring call to {transfer_to}")

        #Перед передачей предупреждаем.
        await ctx.session.generate_reply(
            instructions="Сообщите пользователю, что вы собираетесь их перевести."
        )

        job_ctx = get_job_context()
        try:
            await job_ctx.api.sip.transfer_sip_participant(
                api.TransferSIPParticipantRequest(
                    room_name=job_ctx.room.name,
                    participant_identity=self.participant.identity,
                    transfer_to=f"tel:{transfer_to}",
                )
            )

            logger.info(f"transferred call to {transfer_to}")
        except Exception as e:
            logger.error(f"error transferring call: {e}")
            await ctx.session.generate_reply(
                instructions="there was an error transferring the call."
            )
            await self.hangup()

    @function_tool()
    async def end_call(self, ctx: RunContext):
        """Вызывается, когда пользователь хочет завершить вызов."""
        logger.info(f"ending the call for {self.participant.identity}")

        try:
            await ctx.wait_for_playout()  # Ждём завершения речи
        except Exception as e:
            logger.warning(f"Error waiting for speech playout: {e}")

        # Запускаем завершение
        await self._trigger_end_call()

    def should_end_call(self, text: str) -> bool:
        """Проверяет, содержит ли текст фразы прощания, требующие завершения вызова"""
        import re
        text_lower = text.lower().strip()
        
        # Нормализация: удаляем знаки препинания, оставляем пробелы
        normalized_text = re.sub(r'[^\w\s]', ' ', text_lower)
        normalized_text = ' '.join(normalized_text.split())
        
        # Проверяем наличие ключевых фраз В КОНЦЕ текста (чтобы избежать ложных срабатываний)
        for phrase in self.farewell_phrases:
            if phrase in normalized_text:
                # Дополнительно проверяем, что фраза находится ближе к концу сообщения
                if normalized_text.endswith(phrase) or \
                   len(normalized_text) - normalized_text.find(phrase) < len(phrase) + 5:
                    return True
        return False

    @function_tool()
    async def look_up_availability(
        self,
        ctx: RunContext,
        date: str,
    ):
        """Вызывается, когда пользователь запрашивает информацию 
            о наличии альтернативных вариантов записи на прием.

        Аргументы:
            date: Дата записи на прием, для которой необходимо проверить наличие свободных мест.
        """
        logger.info(
            f"looking up availability for {self.participant.identity} on {date}"
        )
        #await asyncio.sleep(3)
        return {
            "available_times": ["1pm", "2pm", "3pm"],
        }

    @function_tool()
    async def confirm_appointment(
        self,
        ctx: RunContext,
        date: str,
        time: str,
    ):
        """Вызывается, когда пользователь подтверждает свою запись на определенную дату.
        Используйте этот инструмент только в том случае, если вы уверены в дате и времени.

        Аргументы:
            date: Дата записи
            time: Время записи
        """
        logger.info(
            f"confirming appointment for {self.participant.identity} on {date} at {time}"
        )
        return "reservation confirmed"

    @function_tool()
    async def detected_answering_machine(self, ctx: RunContext):
        """Этот инструмент срабатывает, когда звонок поступает на голосовую почту.
        Используйте его ПОСЛЕ того, как услышите приветствие голосовой почты."""
        logger.info(f"detected answering machine for {self.participant.identity}")
        await self.hangup()
