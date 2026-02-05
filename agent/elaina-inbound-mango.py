from __future__ import annotations

import os
import sys

# Добавляем корень проекта в путь для импортов
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Также добавляем путь к текущему каталогу агента
agent_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(agent_dir)

import asyncio
import logging
from livekit import rtc, api
from livekit.agents import (
    AgentSession,
    JobContext,
    RunContext,
    get_job_context,
    cli,
    WorkerOptions,
)
from livekit.agents.llm import ChatMessage

from modules.agent_core import InboundAgent
from modules.config_manager import get_llm_config, get_stt_config, get_tts_config, get_vad_config, get_session_config, initialize_environment, get_config_value
from modules.media_config import setup_vad, setup_stt, setup_tts, setup_llm, setup_session_config, setup_metrics_handler, warmup_llm
from modules.sip_data_handler import process_sip_call_data

# Инициализируем окружение до создания WorkerOptions
initialize_environment()

logger = logging.getLogger("elaina-inbound-worker")
logger.setLevel(logging.INFO)


async def entrypoint(ctx: JobContext):
    logger.info(f"connecting to room {ctx.room.name}")
    await ctx.connect()

    # Для входящего вызова получаем информацию о SIP-участнике из метаданных
    phone_number = "unknown"
    client_name = "Иван"
    
    if ctx.job.metadata:
        # Используем новый обработчик SIP-данных
        phone_number, client_name = process_sip_call_data(
            ctx.job.metadata,
            ctx.room.name,
            ""  # participant_identity пока не известен
        )

    # Создаем агента с информацией о звонящем
    agent = InboundAgent(phone_number=phone_number)

    # Получаем конфигурации
    llm_config = get_llm_config()
    stt_config = get_stt_config()
    tts_config = get_tts_config()
    vad_config = get_vad_config()
    session_config = get_session_config()

    # Создаем компоненты
    vad = setup_vad(vad_config)
    stt = setup_stt(stt_config)
    tts = setup_tts(tts_config)
    llm = setup_llm(llm_config)

    # Создаем конфигурацию сессии
    session_kwargs = setup_session_config(session_config, stt, tts, llm, vad)

    # Пайплайн
    session = AgentSession(**session_kwargs)

    # Настройка обработчика метрик
    setup_metrics_handler(session)

    # Прогрев промпта (Prompt Warmup)
    await warmup_llm(llm, phone_number, client_name)

    # Начинаем сессию агента
    await session.start(agent=agent, room=ctx.room)

    # Ждем подключения участника (SIP-участник будет автоматически добавлен при входящем вызове)
    participant = await ctx.wait_for_participant()  # Ожидаем первого участника
    logger.info(f"participant joined: {participant.identity}")

    # Если номер телефона не был определен ранее, пробуем извлечь из идентификатора участника
    if agent.phone_number == "unknown":
        from modules.sip_data_handler import extract_phone_number_from_participant_identity, identify_client_by_phone
        phone_number = extract_phone_number_from_participant_identity(participant.identity)
        if phone_number:
            agent.client_name = identify_client_by_phone(phone_number)
            agent.phone_number = phone_number

    # Устанавливаем участника в агенте
    agent.set_participant(participant)

    # Сразу говорим фразу приветствия
    await session.say(f'<prosody rate="175%"> Здравствуйте {agent.client_name}, медицинский центр СМИТРА. </prosody> <prosody rate="175%"> Меня зовут Елена, слушаю вас? </prosody>')

    # Добавляем обработчик для отслеживания генерации речи агентом
    @session.on("user_speech_committed")
    def _on_user_speech_committed(user_speech: rtc.SpeechData):
        logger.info(f"Пользователь сказал: {user_speech.text}")
        
        # Проверяем, сказал ли пользователь фразу прощания
        if agent.should_end_call(user_speech.text):
            logger.info("Пользователь сказал фразу прощания, инициируем завершение вызова")
            # Запускаем завершение в контексте текущей сессии
            asyncio.create_task(agent._trigger_end_call())

    # Добавляем обработчик для отслеживания генерации речи агентом
    @session.on("agent_speech_committed")
    def _on_agent_speech_committed(agent_speech: rtc.SpeechData):
        logger.info(f"Агент сказал: {agent_speech.text}")
        
        if agent.call_ended:
            logger.info("Вызов уже завершён, пропускаем обработку")
            return
        
        if agent.should_end_call(agent_speech.text):
            logger.info("Обнаружена фраза прощания в речи агента, инициируем завершение вызова")
            # Запускаем завершение в контексте текущей сессии
            # Используем отложенный вызов, чтобы дать возможность текущему аудио закончиться
            async def delayed_end_call():
                await asyncio.sleep(0.5)  # Даем время для завершения текущей фразы
                await agent._trigger_end_call()
            
            asyncio.create_task(delayed_end_call())

    # Обработчик для случая, когда пользователь покидает комнату
    @session.on("participant_left")
    def _on_participant_left(participant: rtc.Participant):
        logger.info(f"Участник {participant.identity} покинул комнату")
        if not agent.call_ended:
            asyncio.create_task(agent._trigger_end_call())


if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            agent_name="elaina-inbound-mango",
            job_memory_warn_mb=1500,
            ws_url=get_config_value("LIVEKIT_URL"),
            api_key=get_config_value("LIVEKIT_API_KEY"),
            api_secret=get_config_value("LIVEKIT_API_SECRET"),
        )
    )
