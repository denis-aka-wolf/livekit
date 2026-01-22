#!/usr/bin/env python3
"""
Скрипт инициализации SIP конфигураций после запуска LiveKit сервера
"""
import asyncio
import json
import os
import time
from livekit import api


def load_config_from_json(filepath):
    """Загрузка конфигурации из JSON файла"""
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


async def wait_for_livekit_ready(url, timeout=60):
    """Ожидание готовности LiveKit сервера"""
    lk_api = api.LiveKitAPI(url, os.getenv("LIVEKIT_API_KEY", ""), os.getenv("LIVEKIT_API_SECRET", ""))
    
    for _ in range(timeout):
        try:
            # Попытка подключиться к серверу
            await lk_api.room.list_rooms()
            print("LiveKit сервер готов к работе")
            await lk_api.aclose()
            return True
        except Exception as e:
            print(f"Ожидание готовности LiveKit сервера... ({e})")
            await asyncio.sleep(2)
    
    await lk_api.aclose()
    return False


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
        
        # Создание входящего транка
        inbound_config = load_config_from_json("/app/sip/mango_inbound.json")
        if inbound_config:
            try:
                existing_trunks = await sip_client.list_inbound_trunk(api.ListSIPInboundTrunkRequest())
                trunk_exists = any(trunk.name == inbound_config["trunk"]["name"] for trunk in existing_trunks.items)
                
                if not trunk_exists:
                    inbound_request = api.CreateSIPInboundTrunkRequest(
                        name=inbound_config["trunk"]["name"],
                        numbers=inbound_config["trunk"].get("numbers", []),
                        allowed_addresses=inbound_config["trunk"].get("allowed_addresses", [])
                    )
                    inbound_trunk = await sip_client.create_inbound_trunk(inbound_request)
                    print(f"Создан входящий транк: {inbound_trunk.sip_trunk_id}")
                else:
                    print("Входящий транк уже существует")
            except Exception as e:
                print(f"Ошибка при создании входящего транка: {e}")
        
        # Создание исходящего транка
        outbound_config = load_config_from_json("/app/sip/mango_outbound.json")
        if outbound_config:
            try:
                existing_trunks = await sip_client.list_outbound_trunk(api.ListSIPOutboundTrunkRequest())
                trunk_exists = any(trunk.name == outbound_config["trunk"]["name"] for trunk in existing_trunks.items)
                
                if not trunk_exists:
                    outbound_request = api.CreateSIPOutboundTrunkRequest(
                        name=outbound_config["trunk"]["name"],
                        address=outbound_config["trunk"]["address"],
                        numbers=outbound_config["trunk"].get("numbers", [])
                    )
                    outbound_trunk = await sip_client.create_outbound_trunk(outbound_request)
                    print(f"Создан исходящий транк: {outbound_trunk.sip_trunk_id}")
                else:
                    print("Исходящий транк уже существует")
            except Exception as e:
                print(f"Ошибка при создании исходящего транка: {e}")
        
        # Создание правил диспетчеризации
        dispatch_config = load_config_from_json("/app/sip/mango_dispatch.json")
        if dispatch_config:
            try:
                existing_rules = await sip_client.list_dispatch_rule(api.ListSIPDispatchRuleRequest())
                rule_exists = any(rule.name == dispatch_config["dispatch_rule"]["name"] for rule in existing_rules.items)
                
                if not rule_exists:
                    # Найти ID транка по имени для использования в правиле
                    trunk_id = None
                    if "trunk_ids" in dispatch_config["dispatch_rule"]:
                        trunk_id = dispatch_config["dispatch_rule"]["trunk_ids"][0]
                    else:
                        # Если ID транка не указан, ищем по имени
                        inbound_trunks = await sip_client.list_inbound_trunk(api.ListSIPInboundTrunkRequest())
                        for trunk in inbound_trunks.items:
                            if trunk.name == inbound_config["trunk"]["name"]:
                                trunk_id = trunk.sip_trunk_id
                                break
                    
                    if trunk_id:
                        rule_logic = api.SIPDispatchRule(
                            dispatch_rule_direct=api.SIPDispatchRuleDirect(
                                room_name=dispatch_config["dispatch_rule"]["rule"]["dispatch_rule_direct"]["room_name"]
                            )
                        )
                        
                        room_config = None
                        if "room_config" in dispatch_config["dispatch_rule"]:
                            agents = []
                            for agent in dispatch_config["dispatch_rule"]["room_config"]["agents"]:
                                agents.append(api.RoomAgent(identity=agent["agent_name"]))
                            
                            room_config = api.SIPRoomConfig(
                                agents=agents
                            )
                        
                        dispatch_request = api.CreateSIPDispatchRuleRequest(
                            name=dispatch_config["dispatch_rule"]["name"],
                            trunk_ids=[trunk_id],
                            rule=rule_logic,
                            room_config=room_config
                        )
                        
                        dispatch_rule = await sip_client.create_dispatch_rule(dispatch_request)
                        print(f"Создано правило диспетчеризации: {dispatch_rule.sip_dispatch_rule_id}")
                    else:
                        print("Не удалось найти ID транка для правила диспетчеризации")
                else:
                    print("Правило диспетчеризации уже существует")
            except Exception as e:
                print(f"Ошибка при создании правила диспетчеризации: {e}")
        
        print("=== Завершена инициализация SIP конфигураций ===")
        
    except Exception as e:
        print(f"Ошибка при инициализации SIP конфигураций: {e}")
    finally:
        await lk_api.aclose()


if __name__ == "__main__":
    asyncio.run(setup_sip_trunks_and_rules())