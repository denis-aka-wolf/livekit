import asyncio
import os
import sys
import logging
from dotenv import load_dotenv
from livekit import api
from livekit.agents import JobContext, WorkerOptions, cli, JobRequest


# Загружаем переменные из .env файла в корне проекта
load_dotenv("../.env")

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger("enhanced-minimal-agent")


async def request_fnc(req: JobRequest) -> None:
    """Функция для обработки входящих запросов на задачи"""
    logger.info(f"--- ПОЛУЧЕН ЗАПРОС НА ЗАДАЧУ: {req.job.type} ---")
    logger.info(f"Namespace: {req.job.namespace}, Agent name: {req.job.agent_name}")
    await req.accept()


async def entrypoint(ctx: JobContext):
    """Основная функция агента, которая выполняется после принятия задачи"""
    logger.info(f"--- АГЕНТ ЗАШЕЛ В КОМНАТУ: {ctx.room.name} ---")
    await ctx.connect()
    logger.info(f"Агент успешно подключен. Сессия активна.")

    try:
        # Ваша основная логика агента здесь
        while True:
            await asyncio.sleep(10)
            logger.info("Агент активен. Комната: %s", ctx.room.name)
    except asyncio.CancelledError:
        logger.info("Сессия завершена")


if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            request_fnc=request_fnc,
            agent_name="elaina",  # Уникальное имя для этого агента
        )
    )