import os
import logging
from dotenv import load_dotenv

# Настройка логирования
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


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
                        logger.info(f"Загружено значение из .env: {key}={value}")


def initialize_environment():
    """Инициализация окружения с загрузкой .env файла"""
    # Определяем путь к .env файлу в корне проекта
    # config_manager.py -> modules/ -> agent/ -> /srv/livekit (корень проекта)
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")
    logger.info(f"Попытка загрузки .env файла из: {env_path}")
    
    if os.path.exists(env_path):
        logger.info(f".env файл найден: {env_path}")
        load_env_file(env_path)
        logger.info("Завершена загрузка .env файла")
    else:
        logger.warning(f".env файл не найден по пути: {env_path}")
        # Попробуем использовать абсолютный путь к корню проекта
        absolute_env_path = "/srv/livekit/.env"
        if os.path.exists(absolute_env_path):
            logger.info(f"Найден .env файл по абсолютному пути: {absolute_env_path}")
            load_env_file(absolute_env_path)
            logger.info("Завершена загрузка .env файла из абсолютного пути")
        else:
            logger.error("Не найден .env файл ни в одном из возможных мест")


def get_config_value(key: str, default=None):
    """Получение значения конфигурации из переменных окружения"""
    value = os.getenv(key, default)
    logger.debug(f"Получено значение конфигурации: {key} = {value}")
    return value


def get_llm_config():
    """Получение конфигурации для LLM"""
    config = {
        "model": get_config_value("LLAMA_MODEL", "qwen3-4b"),
        "base_url": get_config_value("LLAMA_BASE_URL", "http://127.0.0.1:11434/v1"),
        "api_key": get_config_value("LLM_API_KEY", "no-api-key-required"),  # Для локальных LLM
        "timeout": float(get_config_value("LLM_TIMEOUT", "5.0")),
        "max_retries": int(get_config_value("LLM_MAX_RETRIES", "3")),
    }
    logger.debug(f"Сформирована конфигурация LLM: {config}")
    return config


def get_stt_config():
    """Получение конфигурации для STT"""
    return {
        "base_url": get_config_value("STT_BASE_URL", "http://127.0.0.1:11435/v1"),
        "model": get_config_value("VOXBOX_HF_REPO_ID", "Systran/faster-whisper-small"),
        "api_key": get_config_value("STT_API_KEY", "no-key-needed"),
        "language": get_config_value("STT_LANGUAGE", "ru"),
    }


def get_tts_config():
    """Получение конфигурации для TTS"""
    return {
        "speaker": get_config_value("TTS_SPEAKER", "baya"),
        "sample_rate": int(get_config_value("TTS_SAMPLE_RATE", "48000")),
        "num_channels": int(get_config_value("TTS_NUM_CHANNELS", "1")),
    }


def get_vad_config():
    """Получение конфигурации для VAD (Voice Activity Detection)"""
    return {
        "min_speech_duration": float(get_config_value("VAD_MIN_SPEECH_DURATION", "0.1")),
        "min_silence_duration": float(get_config_value("VAD_MIN_SILENCE_DURATION", "0.5")),
        "prefix_padding_duration": float(get_config_value("VAD_PREFIX_PADDING_DURATION", "0.2")),
    }


def get_session_config():
    """Получение конфигурации для сессии агента"""
    return {
        "min_endpointing_delay": float(get_config_value("SESSION_MIN_ENDPOINTING_DELAY", "0.1")),
        "min_interruption_words": int(get_config_value("SESSION_MIN_INTERRUPTION_WORDS", "2")),
    }