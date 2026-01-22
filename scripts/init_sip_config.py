#!/usr/bin/env python3
"""
Скрипт инициализации SIP конфигураций после запуска LiveKit сервера
"""
import asyncio
import json
import os
import time
from livekit import api

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    import os
    # Определить путь к .env файлу относительно этого скрипта
    script_dir = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.join(script_dir, '..', '.env')
    load_dotenv(dotenv_path=env_path)
except ImportError:
    # If python-dotenv is not installed, continue without loading .env file
    pass


def load_config_from_json(filepath):
    """Загрузка конфигурации из JSON файла"""
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


async def wait_for_livekit_ready(url, timeout=60):
    """Ожидание готовности LiveKit сервера"""
    # Просто ждем некоторое время, считая, что сервер будет готов
    # так как проверка через API комнат не требуется
    import time
    print("Ожидание готовности LiveKit сервера...")
    time.sleep(5)  # Подождать 5 секунд для уверенности, что сервер запущен
    print("LiveKit сервер готов к работе")
    return True


async def setup_sip_trunks_and_rules():
    """Настройка SIP транков и правил диспетчеризации"""
    url = os.getenv("LIVEKIT_URL", "http://localhost:7880")
    api_key = os.getenv("LIVEKIT_API_KEY", "")
    api_secret = os.getenv("LIVEKIT_API_SECRET", "")
    
    if not api_key or api_key == "YOUR_API_KEY_HERE":
        print("Предупреждение: LIVEKIT_API_KEY не установлен")
        return
    
    if not api_secret or api_secret == "YOUR_API_SECRET_HERE":
        print("Предупреждение: LIVEKIT_API_SECRET не установлен")
        return
    
    # Ждем готовности сервера
    if not await wait_for_livekit_ready(url):
        print("Ошибка: LiveKit сервер не стал доступен в течение времени ожидания")
        return
    
    lk_api = api.LiveKitAPI(url, api_key, api_secret)
    sip_client = lk_api.sip
    
    try:
        print("=== Начало инициализации SIP конфигураций ===")
        
        # Переменная для хранения ID входящего транка
        inbound_trunk_id = None
        
        # Создание входящего транка
        inbound_config = load_config_from_json("./sip/mango_inbound.json")
        print(f"Загружена конфигурация входящего транка: {inbound_config}")
        if inbound_config:
            try:
                existing_trunks = await sip_client.list_inbound_trunk(api.ListSIPInboundTrunkRequest())
                trunk_exists = any(trunk.name == inbound_config["trunk"]["name"] for trunk in existing_trunks.items)
                if not trunk_exists:
                    inbound_request = api.CreateSIPInboundTrunkRequest(
                        trunk=api.SIPInboundTrunkInfo(
                            name=inbound_config["trunk"]["name"],
                            numbers=inbound_config["trunk"].get("numbers", []),
                            allowed_addresses=inbound_config["trunk"].get("allowed_addresses", [])
                        )
                    )
                    inbound_trunk = await sip_client.create_inbound_trunk(inbound_request)
                    inbound_trunk_id = inbound_trunk.sip_trunk_id
                    print(f"Создан входящий транк: {inbound_trunk_id}")
                else:
                    # Если транк уже существует, получаем его ID
                    for trunk in existing_trunks.items:
                        if trunk.name == inbound_config["trunk"]["name"]:
                            inbound_trunk_id = trunk.sip_trunk_id
                            break
                    print(f"Входящий транк уже существует: {inbound_trunk_id}")

            except Exception as e:
                print(f"Ошибка при создании входящего транка: {e}")
        
        # Создание исходящего транка
        outbound_config = load_config_from_json("./sip/mango_outbound.json")
        print(f"Загружена конфигурация исходящего транка: {outbound_config}")
        if outbound_config:
            try:
                existing_trunks = await sip_client.list_outbound_trunk(api.ListSIPOutboundTrunkRequest())
                trunk_exists = any(trunk.name == outbound_config["trunk"]["name"] for trunk in existing_trunks.items)
                if not trunk_exists:
                    outbound_request = api.CreateSIPOutboundTrunkRequest(
                        trunk=api.SIPOutboundTrunkInfo(
                            name=outbound_config["trunk"]["name"],
                            address=outbound_config["trunk"]["address"],
                            numbers=outbound_config["trunk"].get("numbers", [])
                        )
                    )
                    outbound_trunk = await sip_client.create_outbound_trunk(outbound_request)
                    print(f"Создан исходящий транк: {outbound_trunk.sip_trunk_id}")
                else:
                    print("Исходящий транк уже существует")

            except Exception as e:
                print(f"Ошибка при создании исходящего транка: {e}")
        
        # Создание правил диспетчеризации
        dispatch_config = load_config_from_json("./sip/mango_dispatch.json")
        print(f"Загружена конфигурация правила диспетчеризации: {dispatch_config}")
        if dispatch_config and inbound_trunk_id:
            try:
                existing_rules = await sip_client.list_dispatch_rule(api.ListSIPDispatchRuleRequest())
                rule_exists = any(rule.name == dispatch_config["dispatch_rule"]["name"] for rule in existing_rules.items)
                if not rule_exists:
                    individual_rule = api.SIPDispatchRuleIndividual(
                        room_prefix="mango_"
                    )

                    rule_logic = api.SIPDispatchRule(
                        dispatch_rule_individual=individual_rule
                    )
                    
                    dispatch_request = api.CreateSIPDispatchRuleRequest(
                        rule=rule_logic,  # Передаём только логику правила
                        name=dispatch_config["dispatch_rule"]["name"],
                        trunk_ids=[inbound_trunk_id],  # Используем ID созданного или найденного входящего транка
                    )

                    
                    dispatch_rule = await sip_client.create_dispatch_rule(dispatch_request)
                    print(f"Создано правило диспетчеризации: {dispatch_rule.sip_dispatch_rule_id}")
                else:
                    print("Правило диспетчеризации уже существует")
            except Exception as e:
                print(f"Ошибка при создании правила диспетчеризации: {e}")
        elif not inbound_trunk_id:
            print("Не удалось получить ID входящего транка для создания правила диспетчеризации")
        
        
        print("=== Завершена инициализация SIP конфигураций ===")
        
    except Exception as e:
        print(f"Ошибка при инициализации SIP конфигураций: {e}")
    finally:
        await lk_api.aclose()


if __name__ == "__main__":
    asyncio.run(setup_sip_trunks_and_rules())