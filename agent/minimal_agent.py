import asyncio
import logging
import os
from dotenv import load_dotenv

# Важно: используем AgentSession для работы с Realtime/LLM
from livekit.agents import AgentServer, JobContext, cli
from livekit.plugins import openai

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

server = AgentServer()

@server.rtc_session()
async def entrypoint(ctx: JobContext):
    # Фильтр комнаты
    if ctx.room.name != "my_room":
        logger.info(f"Skipping room {ctx.room.name}")
        return 

    # Правильная настройка LLM для локального сервера (llama.cpp)
    # Используем OpenAI плагин, так как llama.cpp имитирует его API
    llm = openai.LLM(
        base_url=os.getenv("LLAMA_BASE_URL", "http://localhost:11434/v1"),
        api_key="fake-key", # локальные серверы обычно не требуют ключ
        model=os.getenv("LLAMA_MODEL", "qwen3-4b")
    )
    
    logger.info(f"Connected to room: {ctx.room.name}")
    
    # Подключаемся к комнате
    await ctx.connect()

    while True:
        # Вместо получения списка участников используем num_participants
        logger.info(f"Number of participants in room: {ctx.room.num_participants}")
        
        await asyncio.sleep(60)

if __name__ == "__main__":
    # cli.run_app сам подтянет LIVEKIT_API_KEY и SECRET из среды
    cli.run_app(server)
