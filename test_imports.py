#!/usr/bin/env python3
"""
Тестовый скрипт для проверки корректности импортов в новой архитектуре агента
"""

try:
    print("Проверка импортов для новой архитектуры агента...")

    # Тестируем импорт основных модулей
    from agent.modules.agent_core import InboundAgent
    print("✓ Успешно импортирован InboundAgent")

    from agent.modules.config_manager import initialize_environment, get_llm_config
    print("✓ Успешно импортирован config_manager")

    from agent.modules.prompt_processor import load_and_process_prompt
    print("✓ Успешно импортирован prompt_processor")

    from agent.modules.call_controller import trigger_end_call
    print("✓ Успешно импортирован call_controller")

    from agent.modules.sip_data_handler import process_sip_call_data
    print("✓ Успешно импортирован sip_data_handler")

    from agent.modules.media_config import setup_vad, setup_stt, setup_tts, setup_llm
    print("✓ Успешно импортирован media_config")

    print("\nВсе импорты модулей прошли успешно! Новая архитектура готова к использованию.")
    
except ImportError as e:
    print(f"✗ Ошибка импорта: {e}")
except Exception as e:
    print(f"✗ Непредвиденная ошибка: {e}")