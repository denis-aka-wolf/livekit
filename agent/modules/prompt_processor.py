import os
import logging

logger = logging.getLogger(__name__)


def load_prompt_template():
    """Загружает шаблон промпта из markdown файла"""
    
    # Определяем путь к файлу с промптом
    prompt_file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'elaina-inbound-mango.md')
    logger.info(f"Попытка загрузки шаблона промпта из: {prompt_file_path}")
    
    # Читаем содержимое файла
    try:
        with open(prompt_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            logger.info(f"Шаблон промпта успешно загружен из: {prompt_file_path}")
    except FileNotFoundError:
        logger.error(f"Файл шаблона промпта не найден: {prompt_file_path}")
        raise
    except Exception as e:
        logger.error(f"Ошибка при чтении шаблона промпта: {e}")
        raise
        
    # Извлекаем только содержимое после заголовка первого уровня
    lines = content.split('\n')
    start_idx = -1
    for i, line in enumerate(lines):
        if line.startswith('## Системный промпт для агента Елена'):
            start_idx = i + 1
            break
    
    if start_idx != -1:
        # Возвращаем всё содержимое после заголовка
        return '\n'.join(lines[start_idx:]).strip()
    else:
        # Если заголовок не найден, возвращаем весь контент
        return content.strip()


def load_and_process_prompt(phone_number: str, client_name: str):
    """Загружает и обрабатывает шаблон промпта с подстановкой переменных"""
    prompt_template = load_prompt_template()
    # Подставляем переменные в промпт
    processed_prompt = prompt_template.format(phone_number=phone_number, client_name=client_name)
    return processed_prompt


def validate_prompt_content(content: str) -> bool:
    """Проверяет, что содержимое промпта содержит обязательные элементы"""
    required_elements = ['{phone_number}', '{client_name}']
    for element in required_elements:
        if element not in content:
            return False
    return True


def get_system_prompt_with_context(phone_number: str, client_name: str) -> str:
    """Получает системный промпт с контекстом клиента"""
    template = load_prompt_template()
    if validate_prompt_content(template):
        return template.format(phone_number=phone_number, client_name=client_name)
    else:
        # Если шаблон некорректен, возвращаем базовый вариант
        return f"""Номер телефона клиента: {phone_number}.
Имя клиента: {client_name}

Ты — профессиональный медицинский регистратор Елена сети многопрофильных клиник "СМИТРА". Твоя цель: грамотно проконсультировать пациента, записать его на прием и создать атмосферу заботы."""