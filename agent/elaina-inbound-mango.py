from __future__ import annotations

import asyncio
import logging
from dotenv import load_dotenv
import json
import os
import sys

from typing import Any

from livekit import rtc, api
from livekit.agents import (
    AgentSession,
    Agent,
    JobContext,
    function_tool,
    RunContext,
    get_job_context,
    cli,
    WorkerOptions,
    # RoomInputOptions,
    # RoomOptions,
)
from livekit.plugins import (
    openai,
#    cartesia,
    silero,
    # noise_cancellation,  # noqa: F401 - commented out to prevent cloud filters
)
from livekit.plugins.turn_detector.multilingual import MultilingualModel
# Добавляем родительскую директорию в sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from elaina_tts.elaina_tts import ElainaTTS

logger = logging.getLogger("elaina-inbound-worker")
logger.setLevel(logging.INFO)

def load_env_file(env_path):
    """Загрузка .env файла вручно для избежания проблем с символами возврата каретки"""
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()  # Удаляем все концевые пробелы, включая \r и \n
                if line and not line.startswith('#'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        # Удаляем потенциальные символы возврата каретки из значения
                        value = value.strip().rstrip('\r\n\t ')
                        os.environ[key] = value

# Загружаем .env файл вручно для предотвращения проблем с символами возврата каретки
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
load_env_file(env_path)


class InboundAgent(Agent):
    def __init__(self, *, phone_number: str = ""):
        super().__init__(
            instructions=f"""
Номер телефона клиента: {phone_number}.
Имя клиента: Иван

Ты — виртуальный агент Елена, 21 год, работаешь медицинским регистратором в многопрофильной клинике СМИТРА. 

Твоя задача — подтверждать или переносить запись клиента на приём.

Правила работы:

Не здоровайся, сразу отвечай пользователю
Используй только деловой, вежливый тон.
Общайся строго в рамках темы:
подтверждение записи;
перенос приёма на другое время/дату.

Если клиент задаёт вопросы о клинике, услугах, ценах или иных темах, отвечай:
«Я могу помочь только с подтверждением записи или её переносом. Для других вопросов, пожалуйста, обратитесь в регистратуру.»

Никогда не выходи за рамки сценария. Не предлагай дополнительную информацию.

Сценарий диалога:

Не здаровайся, сразу начинай диалог

Получение имени и проверка записи
Если запись найдена:
«Василий, подтверждаю вашу запись на тридцатое января в девятьнадцать тридцать к врачу Иванову Ивану Ивановичу. Всё верно?»

Если запись не найдена:
«К сожалуйста, уточните дату и время приёма.»

Подтверждение или перенос
Если клиент подтверждает:
«Запись подтверждена. Ждём вас тридцатого января в девятьнадцать тридцать. Если потребуется перенести приём, сообщите — помогу подобрать удобное время.»

Если клиент хочет перенести:
«Поняла, вы хотите перенести приём. Есть свободные слоты: первого февраля на двенадцать часов и пятого февраля на вечер в девятьнадцать тридцать. Какое время вам подходит?»

После выбора клиента:
«Записала вас на пятое февраля в девятьнадцать тридцать к Иванову Ивану Ивановичу. Подтверждаете?»

При подтверждении:

Завершение разговора
«Спасибо за обращение! Хорошего дня!»

Ограничения:
Не используй сленг, эмодзи или неформальные выражения.
Не обсуждай медицинские вопросы.
Если клиент настаивает на информации вне твоей компетенции, повторяй шаблон
Время разговора — не более 2 минут.
Ответ должен быть не более 20-30 слов.
Все цифры пиши текстом, не используй сокращения

Примеры ответов:
На вопрос «Сколько стоит лечение?» → «Я могу помочь только с подтверждением записи или её переносом…»
На благодарность → «Рада помочь! До свидания.»
При неясном запросе → «Пожалуйста, уточните, хотите ли вы подтвердить или перенести запись?»

Свободные слоты:
Иванов Иван Иванович - первого февраля на двенадцать часов и пятого февраля на вечер в девятьнадцать тридцать
   """
        )
        # keep reference to the participant for transfers
        self.participant: rtc.RemoteParticipant | None = None

        self.phone_number = phone_number

    def set_participant(self, participant: rtc.RemoteParticipant):
        self.participant = participant

    async def hangup(self):
        """Вспомогательная функция для завершения вызова путем удаления комнаты."""

        job_ctx = get_job_context()
        await job_ctx.api.room.delete_room(
            api.DeleteRoomRequest(
                room=job_ctx.room.name,
            )
        )

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

        # let the agent finish speaking
        current_speech = ctx.session.current_speech
        if current_speech:
            await current_speech.wait_for_playout()

        await self.hangup()

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
        await asyncio.sleep(3)
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


async def entrypoint(ctx: JobContext):
    logger.info(f"connecting to room {ctx.room.name}")
    await ctx.connect()

    # Для входящего вызова получаем информацию о SIP-участнике из метаданных
    sip_data = {}
    if ctx.job.metadata:
        try:
            sip_data = json.loads(ctx.job.metadata)
            logger.info(f"SIP metadata received: {sip_data}")
        except json.JSONDecodeError:
            logger.warning("Could not decode job metadata as JSON")
    
    # Получаем номер телефона из SIP-информации
    # Пытаемся получить номер из разных возможных полей
    phone_number = sip_data.get("sip_from_user") or sip_data.get("from_user") or sip_data.get("to_user", "unknown")
    logger.info(f"Phone number determined: {phone_number}")

    # Создаем агента с информацией о звонящем
    agent = InboundAgent(phone_number=phone_number)

    llama_model = os.getenv("LLAMA_MODEL", "qwen3-4b")
    llama_base_url = os.getenv("LLAMA_BASE_URL", "http://127.0.0.1:11434/v1")
    #aidar, baya, kseniya, xenia, eugene
    elaina_tts = ElainaTTS(speaker="baya", sample_rate=48000, num_channels=1)

    # Пайплайн
    session = AgentSession(
        turn_detection=MultilingualModel(), # Отвечает за интеллектуальное определение конца фразы
        vad=silero.VAD.load(
            min_speech_duration=0.1,      # Минимальная длительность речи для детекции (увеличено для снижения нагрузки)
            min_silence_duration=0.5,     # Минимальная тишина перед завершением речи (увеличено для лучшей стабильности)
            prefix_padding_duration=0.2,   # Время предварительной задержки для более быстрой детекции
            #sample_rate=16000              # Частота дискретизации (поддерживаются только 8000 и 16000)
        ), # Определяет наличие человеческой речи в аудиопотоке
        # Главные ручки скорости:
        min_endpointing_delay=0.3, # Задержка после VAD (увеличено для более стабильной работы)
        #intent_threshold=0.9,       # Уверенность в завершении намерения
        stt=openai.STT(
            base_url="http://127.0.0.1:11435/v1",
            model=os.getenv("VOXBOX_HF_REPO_ID", "Systran/faster-whisper-small"),
            api_key="no-key-needed",
            language="ru",
        ),
        tts=elaina_tts,
        llm=openai.LLM(
            base_url=llama_base_url,
            model=llama_model,
            api_key="no-key-needed",
            timeout=120.0,  # Увеличенный таймаут для генерации ответа
            max_retries=3,  # Количество попыток при ошибках
        ),
    )

    # Начинаем сессию агента
    await session.start(agent=agent, room=ctx.room)

    # Ждем подключения участника (SIP-участник будет автоматически добавлен при входящем вызове)
    participant = await ctx.wait_for_participant()  # Ожидаем первого участника
    logger.info(f"participant joined: {participant.identity}")

    # Устанавливаем участника в агенте
    agent.set_participant(participant)

    # Сразу говорим фразу приветствия
    await session.say('<prosody rate="fast"> Здравствуйте Иван, медицинский центр СМИТРА. Меня зовут Елена, слушаю вас? </prosody>')


if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            agent_name="elaina-inbound-mango",
            job_memory_warn_mb=8000, 
        )
    )

