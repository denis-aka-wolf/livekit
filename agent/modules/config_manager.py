import os
from dotenv import load_dotenv


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


def initialize_environment():
    """Инициализация окружения с загрузкой .env файла"""
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    load_env_file(env_path)


def get_config_value(key: str, default=None):
    """Получение значения конфигурации из переменных окружения"""
    return os.getenv(key, default)


def get_llm_config():
    """Получение конфигурации для LLM"""
    return {
        "model": get_config_value("LLAMA_MODEL", "qwen3-4b"),
        "base_url": get_config_value("LLAMA_BASE_URL", "http://127.0.0.1:11434/v1"),
        "timeout": float(get_config_value("LLM_TIMEOUT", "5.0")),
        "max_retries": int(get_config_value("LLM_MAX_RETRIES", "3")),
    }


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