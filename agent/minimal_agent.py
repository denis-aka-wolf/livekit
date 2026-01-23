import asyncio
import logging
import os
from itertools import chain
from dotenv import load_dotenv
from google.protobuf.json_format import MessageToDict

# Важно: используем AgentSession для работы с Realtime/LLM
from livekit.agents import Agent, AgentServer, JobContext, cli
from livekit.plugins import openai

logger = logging.getLogger("minimal-worker")
logger.setLevel(logging.INFO)

load_dotenv("../.env")

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
    
    agent = Agent(
        llm=llm, 
        instructions="You are a helpful assistant"
    )
    
    # Запускаем агента в комнате
    await agent.start(ctx.room)
    logger.info(f"Connected to room: {ctx.room.name}")

    while True:
        rtc_stats = await ctx.room.get_session_stats()
        all_stats = chain(
            (("PUBLISHER", stats) for stats in rtc_stats.publisher_stats),
            (("SUBSCRIBER", stats) for stats in rtc_stats.subscriber_stats),
        )

        for source, stats in all_stats:
            stats_kind = stats.WhichOneof("stats")
            logger.info(
                f"RtcStats - {stats_kind} - {source}", 
                extra={"stats": MessageToDict(stats)}
            )
        await asyncio.sleep(60)

if __name__ == "__main__":
    # cli.run_app сам подтянет LIVEKIT_API_KEY и SECRET из среды
    cli.run_app(server)
