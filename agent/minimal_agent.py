import asyncio
import logging
from dotenv import load_dotenv
from livekit import rtc
from livekit.agents import AgentServer, JobContext, cli


logger = logging.getLogger("agent")
load_dotenv("../.env")  # используем основной .env файл

server = AgentServer()

@server.rtc_session()
async def minimal_agent(ctx: JobContext):
    logger.info(f"Подключение к комнате: {ctx.room.name}")
    await ctx.connect()
    try:
        while True:
            await asyncio.sleep(10)
            logger.info("Агент активен. Комната: %s", ctx.room.name)
    except asyncio.CancelledError:
        logger.info("Сессия завершена")

if __name__ == "__main__":
    cli.run_app(server)
