import asyncio
import logging
from dotenv import load_dotenv
from livekit import rtc
from livekit.agents import JobContext, WorkerOptions, cli, JobRequest


logger = logging.getLogger("agent")
load_dotenv("../.env")  # используем основной .env файл


async def request_fnc(req: JobRequest) -> None:
    """Функция для обработки входящих запросов на задачи"""
    logger.info(f"--- ПОЛУЧЕН ЗАПРОС НА ЗАДАЧУ: {req.job.type} ---")
    logger.info(f"Namespace: {req.job.namespace}, Agent name: {req.job.agent_name}")
    await req.accept()


async def entrypoint(ctx: JobContext):
    logger.info(f"Подключение к комнате: {ctx.room.name}")
    await ctx.connect()
    
    # Ждем, пока в комнате появятся другие участники
    sip_participant = None
    
    # Ищем SIP участника среди уже подключенных
    for identity, participant in ctx.room.remote_participants.items():
        if identity.startswith('sip_'):
            sip_participant = participant
            logger.info(f"Найден SIP участник: {identity}")
            break
    
    # Если SIP участник еще не вошел, ждем его
    if not sip_participant:
        logger.info("Ожидаем подключения SIP участника...")
        async for event in ctx.room.subscribe_events():
            if isinstance(event, rtc.ParticipantConnectedEvent):
                if event.participant.identity.startswith('sip_'):
                    sip_participant = event.participant
                    logger.info(f"SIP участник подключен: {sip_participant.identity}")
                    break
    
    try:
        # Просто подтверждаем, что агент активен
        logger.info("Агент успешно подключен к комнате с SIP участником")
        
        # Подписываемся на аудио дорожки SIP участника
        if sip_participant:
            for sid, publication in sip_participant.tracks.items():
                if publication.kind == rtc.TrackKind.KIND_AUDIO:
                    await publication.subscribe()
                    logger.info(f"Подписались на аудио дорожку: {publication.sid}")
        
        # Обрабатываем новые аудио дорожки
        if sip_participant:
            @sip_participant.on("track_published")
            def on_track_published(publication: rtc.RemoteTrackPublication, participant: rtc.RemoteParticipant):
                if publication.kind == rtc.TrackKind.KIND_AUDIO:
                    logger.info(f"Новая аудио дорожка от {participant.identity}: {publication.sid}")
                    asyncio.create_task(publication.subscribe())
        
        # Основной цикл работы агента
        while True:
            await asyncio.sleep(10)
            logger.info("Агент активен. Комната: %s", ctx.room.name)
            
            # Проверяем, остались ли участники в комнате
            if ctx.room.num_participants <= 1:  # <= 1 потому что агент тоже участник
                logger.info("Все участники покинули комнату, завершаем сессию")
                break
                
    except asyncio.CancelledError:
        logger.info("Сессия агента отменена")


if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            request_fnc=request_fnc,
            agent_name="elaina",  # Уникальное имя для этого агента
        )
    )
