import logging
from dotenv import load_dotenv
from livekit import rtc
from livekit.agents import AgentServer, JobContext, cli


logger = logging.getLogger("agent")
load_dotenv(".env.local")  # если используете .env.local

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
    import os
    # Явно задаём переменные окружения
    os.environ["LIVEKIT_URL"] = "ws://158.160.2.82:7880"
    os.environ["LIVEKIT_ROOM"] = "test-room"
    os.environ["LIVEKIT_API_KEY"] = "APImmvWFZNCYdk6"      # замените на ваш ключ
    os.environ["LIVEKIT_API_SECRET"] = "uHPsJbenS3sLS4X8rZHqph61bT5QlTWnHnTNsR2r92a"  # замените на ваш секрет

    cli.run_app(server)
