import asyncio
import logging
import os
import sys
from typing import Any, Dict

# Добавляем путь к elaina_tts
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'elaina_tts'))

from livekit import rtc
from livekit.agents import metrics, MetricsCollectedEvent
from livekit.agents.llm import ChatMessage
from livekit.plugins import openai, silero
from elaina_tts.elaina_tts import ElainaTTS

logger = logging.getLogger("elaina-inbound-worker")
logger.setLevel(logging.INFO)


def setup_vad(config: Dict[str, Any]):
    """Настройка Voice Activity Detection"""
    return silero.VAD.load(
        min_speech_duration=config["min_speech_duration"],
        min_silence_duration=config["min_silence_duration"],
        prefix_padding_duration=config["prefix_padding_duration"],
    )


def setup_stt(config: Dict[str, Any]):
    """Настройка Speech-to-Text"""
    # Получаем URL и проверяем, является ли он локальным
    base_url = config.get("base_url", "")
    logger.info(f"Setting up STT with config: base_url={base_url}, model={config.get('model')}")
    
    # Для локальных сервисов используем специфические настройки, как в оригинальном рабочем коде
    if base_url and ("localhost" in base_url or "127.0.0.1" in base_url or "0.0.0.0" in base_url):
        logger.info(f"Using local STT service: {base_url}")
        # Для локальных STT сервисов (например, whisper-asr-server) с правильными параметрами
        return openai.STT(
            base_url=config["base_url"],
            model=config.get("model", "Systran/faster-whisper-small"),  # Используем значение из конфига, а не getenv напрямую
            api_key=config.get("api_key", "no-key-needed"),  # Используем стандартный ключ для локальных сервисов
            language=config.get("language", "ru"),
        )
    else:
        logger.info(f"Using external STT service: {base_url}")
        # Если это внешний API OpenAI
        return openai.STT(
            base_url=config["base_url"],
            model=config["model"],
            api_key=config["api_key"],
            language=config["language"],
        )


def setup_tts(config: Dict[str, Any]):
    """Настройка Text-to-Speech"""
    return ElainaTTS(
        speaker=config["speaker"],
        sample_rate=config["sample_rate"],
        num_channels=config["num_channels"]
    )


def setup_llm(config: Dict[str, Any]):
    """Настройка Large Language Model"""
    from livekit.plugins.openai import LLM
    
    # Проверяем, является ли URL локальным, и используем соответствующие настройки
    base_url = config.get("base_url", "")
    logger.info(f"Setting up LLM with config: base_url={base_url}, model={config.get('model')}")
    
    if base_url and ("localhost" in base_url or "127.0.0.1" in base_url or "0.0.0.0" in base_url):
        logger.info(f"Using local LLM service: {base_url}")
        # Для локальных LLM (например, Ollama, llama.cpp) с параметрами из оригинального рабочего кода
        return LLM(
            base_url=config["base_url"],
            model=config["model"],
            api_key=config.get("api_key", "no-key-needed"),
            timeout=config.get("timeout", 30.0),  # Используем увеличенный таймаут для локальной модели
            max_retries=config["max_retries"],
        )
    else:
        logger.info(f"Using external LLM service: {base_url}")
        # Для внешнего OpenAI API
        return LLM(
            base_url=config["base_url"],
            model=config["model"],
            api_key=config["api_key"],
            timeout=config["timeout"],
            max_retries=config["max_retries"],
        )


def setup_session_config(session_config: Dict[str, Any], stt, tts, llm, vad):
    """Создание конфигурации сессии агента"""
    return {
        # turn_detection=MultilingualModel(), # Отвечает за интеллектуальное определение конца фразы
        "vad": vad,  # Определяет наличие человеческой речи в аудиопотоке
        # Главные ручки скорости:
        "min_endpointing_delay": session_config["min_endpointing_delay"],
        "min_interruption_words": session_config["min_interruption_words"],
        "stt": stt,
        "tts": tts,
        "llm": llm,
    }


def setup_metrics_handler(session):
    """Настройка обработчика метрик"""
    @session.on("metrics_collected")
    def _on_metrics_collected(ev: MetricsCollectedEvent):
        # Логируем все метрики
        #metrics.log_metrics(ev.metrics)
        
        # Также можем логировать каждую метрику отдельно
        metric_type = type(ev.metrics).__name__
        if metric_type == "EOUMetrics":
            logger.info(f"[VAD] Конец фразы найден через: {ev.metrics.end_of_utterance_delay:.2f}с")
        elif metric_type == "STTMetrics":
            logger.info(f"[STT] Распознано за: {ev.metrics.duration:.2f}с")
        elif metric_type == "LLMMetrics":
            logger.info(f"[LLM] Время до первого слова (TTFT): {ev.metrics.ttft:.2f}с")
            logger.info(f"[LLM] Общая генерация: {ev.metrics.duration:.2f}с")
        elif metric_type == "TTSMetrics":
            logger.info(f"[TTS] Время до начала звука (TTFB): {ev.metrics.ttfb:.2f}с")


async def warmup_llm(llm, phone_number: str, client_name: str):
    """Прогрев модели LLM"""
    try:
        from .prompt_processor import load_and_process_prompt
        warmup_prompt = load_and_process_prompt(phone_number, client_name)
        logger.info("🔥 Начинаю реальный прогрев LLM...")
        # Запускаем чат
        chat_stream = llm.chat(
            history=[ChatMessage(role="system", content=[{"type": "text", "text": warmup_prompt}]),
                     ChatMessage(role="user", content=[{"type": "text", "text": "Привет"}])], # Добавляем имитацию юзера
            temperature=0.7
        )
        # ВАЖНО: нужно прочитать хотя бы один фрагмент из потока, 
        # чтобы llama_cpp начала вычисления
        async for chunk in chat_stream:
            # Нам не нужен текст, нам нужен сам факт обработки
            break 
        logger.info("✅ Prompt warmup completed (кэш создан)")
    except Exception as e:
        logger.warning(f"Prompt warmup failed: {e}")