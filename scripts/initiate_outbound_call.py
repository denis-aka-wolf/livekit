#!/usr/bin/env python3
"""
Скрипт для инициирования исходящего вызова через запущенный агент
Использование: python3 scripts/initiate_outbound_call.py 79133888778
"""

import asyncio
import sys
import os
from dotenv import load_dotenv
from livekit.api import LiveKitAPI
import json

# Загружаем переменные окружения
load_dotenv()

async def initiate_outbound_call(phone_number):
    # Получаем данные из переменных окружения
    url = os.getenv("LIVEKIT_URL", "http://localhost:7880")
    api_key = os.getenv("LIVEKIT_API_KEY")
    api_secret = os.getenv("LIVEKIT_API_SECRET")
    
    if not api_key or not api_secret:
        print("Ошибка: Отсутствуют переменные окружения LIVEKIT_API_KEY или LIVEKIT_API_SECRET")
        return False

    # Создаем экземпляр API
    lk_api = LiveKitAPI(url, api_key, api_secret)

    try:
        print(f"Инициирую исходящий вызов на номер {phone_number} через агента 'elaina-outbound-caller'...")
        
        # Создаем задание для агента
        response = await lk_api.dispatch_create_agent(
            rules={"agentName": "elaina-outbound-caller"},
            metadata=json.dumps({
                "phone_number": phone_number,
                "transfer_to": ""
            }),
            topic="outbound-call"
        )
        
        print(f"Задание для агента создано успешно!")
        print(f"ID задания: {response.sid}")
        print(f"Статус: {response.state}")
        return True
        
    except Exception as e:
        print(f"Ошибка при создании задания для агента: {e}")
        return False
    finally:
        await lk_api.aclose()

async def main():
    if len(sys.argv) != 2:
        print("Использование: python3 scripts/initiate_outbound_call.py <номер_телефона>")
        print("Пример: python3 scripts/initiate_outbound_call.py 79133888778")
        sys.exit(1)
    
    phone_number = sys.argv[1]
    
    # Проверяем формат номера телефона
    if not phone_number.isdigit() and not (phone_number.startswith('+') and phone_number[1:].isdigit()):
        print("Номер телефона должен состоять только из цифр, либо начинаться с '+' и содержать цифры")
        sys.exit(1)
    
    success = await initiate_outbound_call(phone_number)
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())