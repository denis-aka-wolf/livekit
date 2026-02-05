import json
import logging
import re
from typing import Dict, Optional

logger = logging.getLogger("elaina-inbound-worker")
logger.setLevel(logging.INFO)


def parse_sip_metadata(metadata: str) -> Dict:
    """Парсит метаданные SIP-вызова из строки JSON"""
    try:
        sip_data = json.loads(metadata)
        logger.info(f"SIP metadata received: {sip_data}")
        return sip_data
    except json.JSONDecodeError:
        logger.warning("Could not decode job metadata as JSON")
        return {}


def extract_phone_number_from_sip_data(sip_data: Dict) -> str:
    """Извлекает номер телефона из SIP-данных"""
    # Пытаемся получить номер из разных возможных полей
    phone_number = sip_data.get("sip_from_user") or sip_data.get("from_user") or sip_data.get("to_user", "unknown")
    return phone_number


def extract_phone_number_from_room_name(room_name: str) -> Optional[str]:
    """Извлекает номер телефона из названия комнаты"""
    room_phone_match = re.search(r'_(\d{11})_', room_name)
    if room_phone_match:
        return room_phone_match.group(1)
    return None


def extract_phone_number_from_participant_identity(identity: str) -> Optional[str]:
    """Извлекает номер телефона из идентификатора участника"""
    if identity and identity.startswith('sip_'):
        return identity[4:]  # Убираем префикс 'sip_'
    return None


def identify_client_by_phone(phone_number: str) -> str:
    """Определяет имя клиента по номеру телефона"""
    phone_to_name = {
        "79133888778": "Денис Сергеевич",
        "79955701443": "Денис",
        "79137296699": "Павел",
        "79831379240": "Артем"
    }
    return phone_to_name.get(phone_number, "Иван")


def process_sip_call_data(metadata: str, room_name: str, participant_identity: str) -> tuple[str, str]:
    """Обрабатывает все данные SIP-вызова и возвращает номер телефона и имя клиента"""
    # Парсим метаданные
    sip_data = parse_sip_metadata(metadata)
    
    # Извлекаем номер телефона из SIP-данных
    phone_number = extract_phone_number_from_sip_data(sip_data)
    
    # Если номер не найден в SIP-данных, пробуем извлечь из названия комнаты
    if phone_number == "unknown":
        room_phone = extract_phone_number_from_room_name(room_name)
        if room_phone:
            phone_number = room_phone
    
    # Если все еще не найден, пробуем извлечь из идентификатора участника
    if phone_number == "unknown":
        identity_phone = extract_phone_number_from_participant_identity(participant_identity)
        if identity_phone:
            phone_number = identity_phone
    
    logger.info(f"Phone number determined: {phone_number}")
    
    # Определяем имя клиента по номеру телефона
    client_name = identify_client_by_phone(phone_number)
    
    return phone_number, client_name


def get_sip_headers_info(sip_data: Dict) -> Dict:
    """Извлекает информацию из SIP-заголовков"""
    headers_info = {}
    
    # Извлекаем часто используемые поля
    for key in ['sip_from_user', 'sip_to_user', 'sip_call_id', 'sip_from_host', 'sip_to_host']:
        if key in sip_data:
            headers_info[key] = sip_data[key]
    
    return headers_info