import logging
import os
from dotenv import load_dotenv
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    cli,
)
from livekit.plugins import openai, silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel


logger = logging.getLogger("simple-answer-agent")
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


class SimpleAnswerAgent(Agent):
    def __init__(self) -> None:
        # Используем минимальные инструкции - просто поднять трубку
        super().__init__(
            instructions="Вы поднимаете трубку и слушаете собеседника. Не говорите ничего.",
        )

    async def on_enter(self) -> None:
        """Вызывается при входе в сессию - поднятие трубки"""
        print("Агент вошел в комнату - поднятие трубки")


server = AgentServer()


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


server.setup_fnc = prewarm


@server.rtc_session()
async def simple_answer_agent(ctx: JobContext):
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    # Создаем минимальную сессию агента - только для поднятия трубки
    session = AgentSession(
        stt=None,  # Отключаем STT
        llm=None,  # Отключаем LLM
        tts=None,  # Отключаем TTS
        turn_detection=None,  # Отключаем детекцию речи
        vad=ctx.proc.userdata["vad"],
        preemptive_generation=False,  # Отключаем предгенерацию
    )

    await session.start(
        agent=SimpleAnswerAgent(),
        room=ctx.room,
    )

    await ctx.connect()


if __name__ == "__main__":
    cli.run_app(server)