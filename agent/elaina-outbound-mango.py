from __future__ import annotations

import asyncio
import logging
from dotenv import load_dotenv
import json
import os
OUTBOUND_TRUNK_ID = "ST_NdEHgspjNRwV"
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
import livekit.plugins.piper_tts as piper_tts

logger = logging.getLogger("elaina-outbound-caller-worker")
logger.setLevel(logging.INFO)

def load_env_file(env_path):
    """Загрузка .env файла вручную для избежания проблем с символами возврата каретки"""
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

# Загружаем .env файл вручную для предотвращения проблем с символами возврата каретки
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
load_env_file(env_path)

#outbound_trunk_id = os.getenv("SIP_OUTBOUND_TRUNK_ID")
#outbound_trunk_id = os.getenv("SIP_OUTBOUND_TRUNK_ID", OUTBOUND_TRUNK_ID)
outbound_trunk_id = OUTBOUND_TRUNK_ID
logger.info(f"Используемый SIP trunk: {outbound_trunk_id!r}")


class OutboundCaller(Agent):
    def __init__(
        self,
        *,
        name: str,
        appointment_time: str,
        dial_info: dict[str, Any],
    ):
        super().__init__(
            instructions=f"""
            Вы работаете помощником по планированию в стоматологической клинике. Ваше взаимодействие с пользователем будет осуществляться по телефону.
            Вы будете разговаривать по телефону с пациентом, у которого назначена встреча. 
            Ваша задача — подтвердить детали записи на прием.

            Как представитель службы поддержки клиентов, вы должны быть вежливы и профессиональны во всех ситуациях. 
            Позвольте пользователю завершить разговор.
            Если пользователь хочет, чтобы его перевели к оператору, сначала подтвердите это. 
            После подтверждения используйте инструмент transfer_call.
            
            Имя клиента: {name}. 
            Его запись на прием: {appointment_time}.
            Отвечай только на русском языке.
            Ответы должны быть краткими, так как они озвучиваются голосом.
            Ты отвечаешь только по стоматологической клинике, если клиент говорит на другие темы то возвращай его аккуратно к планированию посещения стоматологической клиники.
            """
        )
        # keep reference to the participant for transfers
        self.participant: rtc.RemoteParticipant | None = None

        self.dial_info = dial_info

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
    async def transfer_call(self, ctx: RunContext):
        """Перевести звонок оператору, после подтверждения пользователя."""

        transfer_to = self.dial_info["transfer_to"]
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

    # При отправке вызова агенту мы передадим ему необходимую информацию для набора номера пользователя.
    # dial_info — это словарь со следующими ключами:
    # - phone_number: номер телефона для набора
    # - transfer_to: номер телефона, на который будет переадресован звонок по запросу
    dial_info = json.loads(ctx.job.metadata)
    participant_identity = phone_number = dial_info["phone_number"]

    # Найти номер телефона пользователя и информацию о встрече
    agent = OutboundCaller(
        name="Denis",
        appointment_time="next Tuesday at 3pm",
        dial_info=dial_info,
    )

    llama_model = os.getenv("LLAMA_MODEL", "qwen3-4b")
    llama_base_url = os.getenv("LLAMA_BASE_URL", "http://127.0.0.1:11434/v1")

    # Пайплайн
    session = AgentSession(
        turn_detection=MultilingualModel(), # Отвечает за интеллектуальное определение конца фразы
        vad=silero.VAD.load(
            min_speech_duration=0.1,       # Минимальная длительность речи для детекции
            min_silence_duration=0.1,      # Минимальная тишина перед завершением речи
            prefix_padding_duration=0.2,   # Время предварительной задержки для более быстрой детекции
            #sample_rate=16000              # Частота дискретизации (поддерживаются только 8000 и 16000)
        ), # Определяет наличие человеческой речи в аудиопотоке
        # Главные ручки скорости:
        min_endpointing_delay=0.15, # Задержка после VAD (ставим 150 мс)
        #intent_threshold=0.9,       # Уверенность в завершении намерения
        stt=openai.STT(
            base_url="http://127.0.0.1:11435/v1",
            model=os.getenv("VOXBOX_HF_REPO_ID", "Systran/faster-whisper-small"),
            api_key="no-key-needed",
            language="ru",
        ),
        tts=piper_tts.TTS(
            base_url="http://localhost:5000/",
        ),

        llm=openai.LLM(
            base_url=llama_base_url,
            model=llama_model,
            api_key="no-key-needed",
        ),
    )

    # Начинаем сессию перед набором номера, чтобы гарантировать, что когда пользователь ответит,
    # агент не пропустит ничего из того, что скажет пользователь.
    session_started = asyncio.create_task(
        session.start(
            agent=agent,
            room=ctx.room
        )
    )

    # `create_sip_participant` начинает набор номера пользователя
    try:
        await ctx.api.sip.create_sip_participant(
            api.CreateSIPParticipantRequest(
                room_name=ctx.room.name,
                sip_trunk_id=outbound_trunk_id,
                sip_call_to=phone_number,
                participant_identity=participant_identity,
                # Функция блокируется до тех пор, пока пользователь не ответит на звонок или если звонок не удастся.
                wait_until_answered=True,
            )
        )

        # Ждем пока клиент присоединится к комнате
        await session_started
        participant = await ctx.wait_for_participant(identity=participant_identity)
        logger.info(f"participant joined: {participant.identity}")

        # Сразу говорим фразу
        await session.say("Здравствуйте, меня зовут Елена. Чем могу быть полезна?")

        agent.set_participant(participant)

    except api.TwirpError as e:
        logger.error(
            f"error creating SIP participant: {e.message}, "
            f"SIP status: {e.metadata.get('sip_status_code')} "
            f"{e.metadata.get('sip_status')}"
        )
        ctx.shutdown()


if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            agent_name="elaina-outbound-caller",
        )
    )

