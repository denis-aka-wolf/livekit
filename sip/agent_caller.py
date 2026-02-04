from __future__ import annotations

import asyncio
import logging
from dotenv import load_dotenv
import json
import os
from typing import Any

# Основные компоненты LiveKit для работы с комнатами и API
from livekit import rtc, api
# Компоненты фреймворка Агентов
from livekit.agents import (
    AgentSession,
    Agent,
    JobContext,
    function_tool,
    RunContext,
    get_job_context,
    cli,
    WorkerOptions,
    RoomInputOptions,
)
# Плагины для распознавания речи (STT), генерации (TTS) и анализа (LLM)
from livekit.plugins import (
    deepgram,
    openai,
    cartesia,
    silero,
    noise_cancellation,  # noqa: F401
)
from livekit.plugins.turn_detector.english import EnglishModel


# Загрузка переменных окружения из файла .env.local (ключи API и ID транка)
load_dotenv(dotenv_path=".env.local")

# Настройка логирования для отслеживания работы в консоли
logger = logging.getLogger("outbound-caller")
logger.setLevel(logging.INFO)

# ID вашего SIP-транка для совершения исходящих звонков (из настроек LiveKit)
outbound_trunk_id = os.getenv("SIP_OUTBOUND_TRUNK_ID")


class OutboundCaller(Agent):
    """Класс, описывающий логику поведения ИИ-агента."""
    def __init__(
        self,
        *,
        name: str,
        appointment_time: str,
        dial_info: dict[str, Any],
    ):
        # Инициализация базового класса Agent с системными инструкциями (Промптом)
        super().__init__(
            instructions=f"""
            Вы — помощник по планированию в стоматологической клинике. Интерфейс общения — голос.
            Вы звоните пациенту, у которого запланирован визит. Ваша цель — подтвердить детали записи.
            Будьте вежливы и профессиональны. Позвольте пользователю самому завершить разговор.

            Если пользователь хочет поговорить с человеком, сначала подтвердите это. 
            После подтверждения используйте инструмент transfer_call.
            Имя клиента: {name}. Запись назначена на: {appointment_time}.
            """
        )
        # Ссылка на участника (пациента), нужна для перевода звонка
        self.participant: rtc.RemoteParticipant | None = None
        # Информация о наборе (номер телефона и куда переводить)
        self.dial_info = dial_info
        
        # Флаг для отслеживания состояния завершения вызова
        self.call_ended = False

    def set_participant(self, participant: rtc.RemoteParticipant):
        """Метод для запоминания ID собеседника, когда он поднимет трубку."""
        self.participant = participant

    async def hangup(self):
        """Вспомогательная функция для завершения звонка через удаление комнаты."""
        job_ctx = get_job_context()
        await job_ctx.api.room.delete_room(
            api.DeleteRoomRequest(
                room=job_ctx.room.name,
            )
        )

    @function_tool()
    async def transfer_call(self, ctx: RunContext):
        """Инструмент: Переводит звонок на живого оператора. 
        Вызывается нейросетью автоматически, если человек попросит оператора."""

        transfer_to = self.dial_info["transfer_to"]
        if not transfer_to:
            return "cannot transfer call"

        logger.info(f"transferring call to {transfer_to}")

        # Просим агента озвучить фразу о переводе перед тем, как разорвать мост
        await ctx.session.generate_reply(
            instructions="Сообщите пользователю, что вы сейчас его переключите"
        )

        job_ctx = get_job_context()
        try:
            # Команда LiveKit для SIP-перевода (Refer)
            await job_ctx.api.sip.transfer_sip_participant(
                api.TransferSIPParticipantRequest(
                    room_name=job_ctx.room.name,
                    participant_identity=self.participant.identity,
                    transfer_to=f"tel:{transfer_to}",
                )
            )

            logger.info(f"Звонок успешно переведен на {transfer_to}")
        except Exception as e:
            logger.error(f"Ошибка при переводе: {e}")
            await ctx.session.generate_reply(
                instructions="Сообщите об ошибке при попытке перевода."
            )
            await self.hangup()

    @function_tool()
    async def end_call(self, ctx: RunContext):
        """Инструмент: Завершает звонок, когда пользователь прощается."""
        logger.info(f"Завершение звонка для {self.participant.identity}")

        # Устанавливаем флаг завершения вызова
        self.call_ended = True

        # Останавливаем любые текущие и будущие попытки генерации речи
        try:
            current_speech = ctx.session.current_speech
            if current_speech:
                await current_speech.wait_for_playout()
        except Exception as e:
            logger.warning(f"Error waiting for speech playout: {e}")

        # Небольшая задержка для обеспечения завершения всех процессов
        await asyncio.sleep(0.5)

        await self.hangup()

    @function_tool()
    async def look_up_availability(
        self,
        ctx: RunContext,
        date: str,
    ):
        """Инструмент: Проверяет доступное время для записи на другую дату."""
        logger.info(
            f"Поиск свободного времени для {self.participant.identity} на дату {date}"
        )
        # Здесь имитируется запрос к базе данных или календарю
        await asyncio.sleep(3)
        return {
            "available_times": ["13:00", "14:00", "15:00"],
        }

    @function_tool()
    async def confirm_appointment(
        self,
        ctx: RunContext,
        date: str,
        time: str,
    ):
        """Инструмент: Подтверждает запись. 
        Используется только когда клиент четко выразил согласие."""
        logger.info(f"Запись подтверждена для {self.participant.identity}  на {date} в {time}")
        return "reservation confirmed"

    @function_tool()
    async def detected_answering_machine(self, ctx: RunContext):
        """Инструмент: Вызывается, если на звонок ответил автоответчик."""
        logger.info(f"Обнаружен автоответчик для {self.participant.identity}")
        await self.hangup()


async def entrypoint(ctx: JobContext):
    """Точка входа: вызывается LiveKit, когда для агента появляется задача (звонок)."""
    logger.info(f"Подключение к комнате {ctx.room.name}")
    await ctx.connect()

    # При отправке вызова агенту мы передадим ему необходимую информацию для набора номера пользователя.
    # dial_info — это словарь со следующими ключами:
    # - phone_number: номер телефона для набора
    # - transfer_to: номер телефона, на который будет переадресован звонок по запросу
    dial_info = json.loads(ctx.job.metadata)
    participant_identity = phone_number = dial_info["phone_number"]

"""    # Найти номер телефона пользователя и информацию о встрече
    agent = OutboundCaller(
        name="Елена",
        appointment_time="следующий вторник в 15-00",
        dial_info=dial_info,
    )

    # Настройка «мозгов» и органов чувств агента:
    session = AgentSession(
        turn_detection=EnglishModel(),  # Определяет, когда человек закончил говорить
        vad=silero.VAD.load(),          # Voice Activity Detection (обнаруживает голос)
        stt=deepgram.STT(),             # Превращает речь человека в текст
        tts=cartesia.TTS(),             # Превращает текст агента в голос
        llm=openai.LLM(model="gpt-4o"), # Основной разум на базе GPT-4o
    )

    # Запускаем сессию ПЕРЕД тем, как набирать номер.
    # Это нужно, чтобы агент был готов слушать сразу, как только человек поднимет трубку.
    session_started = asyncio.create_task(
        session.start(
            agent=agent,
            room=ctx.room,
            room_input_options=RoomInputOptions(
                # Включаем фильтрацию шумов (Krisp) для лучшего качества телефонии
                noise_cancellation=noise_cancellation.BVCTelephony(),
            ),
        )
    )
"""
    # `create_sip_participant` начинает физический набор номера через SIP
    try:
        await ctx.api.sip.create_sip_participant(
            api.CreateSIPParticipantRequest(
                room_name=ctx.room.name,
                sip_trunk_id=outbound_trunk_id,
                sip_call_to=phone_number,
                participant_identity=participant_identity,
                # Ждать до тех пор, пока человек не ответит или вызов не сбросят
                # Важный параметр для телефонии. Код не пойдет дальше, пока на той стороне не снимут трубку. 
                # Это позволяет не начинать приветствие в пустоту.
                wait_until_answered=True,
            )
        )
"""
        # Когда человек ответил, дожидаемся готовности сессии и входа участника в комнату
        await session_started
        participant = await ctx.wait_for_participant(identity=participant_identity)
        logger.info(f"Собеседник подключился: {participant.identity}")

        # Передаем данные участника агенту для возможных манипуляций (перевода звонка)
        agent.set_participant(participant)
"""
        # !!! Бесконечный цикл, чтобы агент не выходил из комнаты
        # Он будет просто «молчать», так как мы не запускали AgentSession
        while True:
            await asyncio.sleep(1)

    except api.TwirpError as e:
        # Обработка ошибок SIP (занято, не в сети, неверный номер)
        logger.error(
            f"Ошибка создания SIP-участника: {e.message}, "
            f"SIP статус: {e.metadata.get('sip_status_code')} "
            f"{e.metadata.get('sip_status')}"
        )
        ctx.shutdown()
    except asyncio.CancelledError:
        logger.info("Звонок завершен или задача отменена")

if __name__ == "__main__":
    # Запуск воркера, который слушает задачи от LiveKit сервера
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            # Имя должно совпадать с тем, что вы вызываете через API
            agent_name="elaina-caller",
        )
    )