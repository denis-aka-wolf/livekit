import logging
import os
from typing import Any

from dotenv import load_dotenv
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    cli,
    function_tool,
    RunContext,
)
from livekit.plugins import silero, openai
# from livekit.plugins.turn_detector.multilingual import MultilingualModel  # Закомментирован для избежания ошибки загрузки модели


logger = logging.getLogger("minimal-worker")
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

class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions="""You are a helpful voice AI assistant. The user is interacting with you via voice, even if you perceive the conversation as text.
            You eagerly assist users with their questions by providing information from your extensive knowledge.
            Your responses are concise, to the point, and without any complex formatting or punctuation including emojis, asterisks, or other symbols.
            You are curious, friendly, and have a sense of humor.""",
        )

    @function_tool()
    async def multiply_numbers(
        self,
        context: RunContext,
        number1: int,
        number2: int,
    ) -> dict[str, Any]:
        """Multiply two numbers.
        
        Args:
            number1: The first number to multiply.
            number2: The second number to multiply.
        """

        return f"The product of {number1} and {number2} is {number1 * number2}."

server = AgentServer()

def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()

server.setup_fnc = prewarm

@server.rtc_session()
async def my_agent(ctx: JobContext):
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    llama_model = os.getenv("LLAMA_MODEL", "qwen3-4b")
    llama_base_url = os.getenv("LLAMA_BASE_URL", "http://127.0.0.1:11434/v1")

    session = AgentSession(
        stt=openai.STT(
            base_url="http://127.0.0.1:80/v1",
            # base_url="http://localhost:11435/v1", # uncomment for local testing
            model="Systran/faster-whisper-small",
            api_key="no-key-needed"
        ),
        llm=openai.LLM(
            base_url=llama_base_url,
            # base_url="http://localhost:11436/v1", # uncomment for local testing
            model=llama_model,
            api_key="no-key-needed"
        ),
        tts=openai.TTS(
            base_url="http://127.0.0.1:8880/v1",
            # base_url="http://localhost:8880/v1", # uncomment for local testing
            model="kokoro",
            voice="af_nova",
            api_key="no-key-needed"
        ),
        turn_detection=None,  #MultilingualModel(), Отключаем turn_detection из-за отсутствия модели model_q8.onnx
        vad=ctx.proc.userdata["vad"],
        preemptive_generation=True,
    )

    await session.start(
        agent=Assistant(),
        room=ctx.room,
    )

    await ctx.connect()

if __name__ == "__main__":
    cli.run_app(server)
