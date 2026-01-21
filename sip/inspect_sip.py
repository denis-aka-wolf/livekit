import asyncio
from livekit import api

# Настройки доступа
URL = "http://158.160.2.82:7880"
API_KEY = ""
API_SECRET = ""

async def inspect_sip():
    lk_api = api.LiveKitAPI(URL, API_KEY, API_SECRET)
    sip_client = lk_api.sip

    print("="*50)
    print("ИНСПЕКЦИЯ SIP НАСТРОЕК LIVEKIT")
    print("="*50)

    # 1. Список входящих транков
    print("\n[1] ВХОДЯЩИЕ ТРАНКИ (Inbound Trunks):")
    try:
        inbound = await sip_client.list_inbound_trunk(api.ListSIPInboundTrunkRequest())
        if not inbound.items:
            print("  Список пуст")
        for item in inbound.items:
            print(f"  - ID: {item.sip_trunk_id}")
            print(f"    Name: {item.name}")
            print(f"    Numbers: {list(item.numbers)}")
            print("-" * 20)
    except Exception as e:
        print(f"  Ошибка при получении входящих транков: {e}")

    # 2. Список исходящих транков
    print("\n[2] ИСХОДЯЩИЕ ТРАНКИ (Outbound Trunks):")
    try:
        outbound = await sip_client.list_outbound_trunk(api.ListSIPOutboundTrunkRequest())
        if not outbound.items:
            print("  Список пуст")
        for item in outbound.items:
            print(f"  - ID: {item.sip_trunk_id}")
            print(f"    Name: {item.name}")
            print(f"    Address: {item.address}")
            print(f"    Numbers: {list(item.numbers)}")
            print("-" * 20)
    except Exception as e:
        print(f"  Ошибка при получении исходящих транков: {e}")

    # 3. Список правил (Dispatch Rules)
    print("\n[3] ПРАВИЛА РАСПРЕДЕЛЕНИЯ (Dispatch Rules):")
    try:
        rules = await sip_client.list_dispatch_rule(api.ListSIPDispatchRuleRequest())
        if not rules.items:
            print("  Список пуст")
        for item in rules.items:
            print(f"  - ID: {item.sip_dispatch_rule_id}")
            print(f"    Name: {item.name}")
            print(f"    Trunk IDs: {list(item.trunk_ids)}")
            # Пытаемся определить тип правила
            if item.rule.HasField("dispatch_rule_individual"):
                prefix = item.rule.dispatch_rule_individual.room_prefix
                print(f"    Type: Individual (Prefix: {prefix})")
            print("-" * 20)
    except Exception as e:
        print(f"  Ошибка при получении правил: {e}")

    await lk_api.aclose()

if __name__ == "__main__":
    asyncio.run(inspect_sip())
