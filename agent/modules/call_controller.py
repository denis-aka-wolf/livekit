import asyncio
import logging

from livekit import rtc, api
from livekit.agents import get_job_context

logger = logging.getLogger("elaina-inbound-worker")
logger.setLevel(logging.INFO)


async def trigger_end_call(participant_identity: str, call_ended_flag: bool):
    """Инициирует завершение вызова с корректной синхронизацией"""
    if call_ended_flag:
        logger.info("Вызов уже завершён, пропускаем дубликат")
        return True  # Указывает, что вызов уже завершен

    logger.info(f"Начинаем завершение вызова для {participant_identity}")
    
    try:
        # Получаем контекст задания
        job_ctx = get_job_context()
        
        # Удаляем комнату для завершения вызова
        if job_ctx.room and hasattr(job_ctx.room, 'name'):
            logger.info(f"Пытаюсь удалить комнату: {job_ctx.room.name}")
            await job_ctx.api.room.delete_room(
                api.DeleteRoomRequest(room=job_ctx.room.name)
            )
            logger.info("Комната удалена, вызов завершён")
        else:
            logger.warning("Комната недоступна для удаления")
            
    except Exception as e:
        logger.error(f"Ошибка при удалении комнаты: {e}")
        
        # Если удаление комнаты не удалось, пробуем альтернативные способы
        try:
            # Попробуем закрыть комнату через другие средства
            if hasattr(job_ctx, 'close'):
                await job_ctx.close()
                
        except Exception as e2:
            logger.error(f"Ошибка при альтернативном завершении вызова: {e2}")
            
    finally:
        logger.info(f"Завершение вызова для {participant_identity} завершено")
        
    return True  # Указывает, что вызов теперь завершен


async def hangup_call(participant_identity: str, call_ended_flag: bool):
    """Завершение вызова с защитой от повторных вызовов"""
    return await trigger_end_call(participant_identity, call_ended_flag)


async def transfer_call_to_operator(transfer_to: str, room_name: str, participant_identity: str):
    """Перевод звонка оператору"""
    if not transfer_to:
        logger.warning("Невозможно перевести вызов - не указан номер для перевода")
        return False

    logger.info(f"Перевод вызова на {transfer_to}")

    job_ctx = get_job_context()
    try:
        await job_ctx.api.sip.transfer_sip_participant(
            api.TransferSIPParticipantRequest(
                room_name=room_name,
                participant_identity=participant_identity,
                transfer_to=f"tel:{transfer_to}",
            )
        )

        logger.info(f"Вызов успешно переведен на {transfer_to}")
        return True
    except Exception as e:
        logger.error(f"Ошибка при переводе вызова: {e}")
        return False


async def handle_detected_answering_machine(participant_identity: str, call_ended_flag: bool):
    """Обработка ситуации, когда звонок поступил на голосовую почту"""
    logger.info(f"Обнаружена голосовая почта для {participant_identity}")
    return await trigger_end_call(participant_identity, call_ended_flag)


def check_farewell_phrases(text: str, farewell_phrases: list[str]) -> bool:
    """Проверяет, содержит ли текст фразы прощания, требующие завершения вызова"""
    import re
    text_lower = text.lower().strip()
    
    # Нормализация: удаляем знаки препинания, оставляем пробелы
    normalized_text = re.sub(r'[^\w\s]', ' ', text_lower)
    normalized_text = ' '.join(normalized_text.split())
    
    # Проверяем наличие ключевых фраз В КОНЦЕ текста (чтобы избежать ложных срабатываний)
    for phrase in farewell_phrases:
        if phrase in normalized_text:
            # Дополнительно проверяем, что фраза находится ближе к концу сообщения
            if normalized_text.endswith(phrase) or \
               len(normalized_text) - normalized_text.find(phrase) < len(phrase) + 5:
                return True
    return False