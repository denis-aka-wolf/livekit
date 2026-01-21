import asyncio
from livekit import api

URL = "http://158.160.2.82:7880"
API_KEY = ""
API_SECRET = ""
INBOUND_TRUNK_ID = "ST_SbAbWDDUgUtP"

async def create_mango_rule():
    lk_api = api.LiveKitAPI(URL, API_KEY, API_SECRET)
    sip_client = lk_api.sip

    print(f"Создание правила для транка {INBOUND_TRUNK_ID}...")

    try:
        # 1. Логика распределения звонка
        individual_rule = api.SIPDispatchRuleIndividual(
            room_prefix="mango_"
        )

        rule_logic = api.SIPDispatchRule(
            dispatch_rule_individual=individual_rule
        )

        # 2. Настройка Агента (исправлено: identity вместо agent_identity)
        room_agent = api.RoomAgent(
            identity="elaina"  # <-- Ключевое изменение!
        )

        # 3. Настройка комнаты
        sip_room_config = api.SIPRoomConfig(
            agents=[room_agent]
        )

        # 4. Финальный запрос (исправлено: rule=rule_logic, а не SIPDispatchRuleInfo)
        request = api.CreateSIPDispatchRuleRequest(
            rule=rule_logic,  # <-- Передаём только логику правила
            name="mango-dispatch",
            trunk_ids=[INBOUND_TRUNK_ID],
            room_config=sip_room_config
        )

        res = await sip_client.create_dispatch_rule(request)
        print(f"Успех! Правило создано. ID: {res.sip_dispatch_rule_id}")

    except Exception as e:
        print(f"Ошибка при создании: {e}")
        print("\nПопробуем без блока agents...")
        try:
            # Запасной вариант без агента
            request_simple = api.CreateSIPDispatchRuleRequest(
                rule=rule_logic,
                name="mango-simple",
                trunk_ids=[INBOUND_TRUNK_ID]
            )
            res_simple = await sip_client.create_dispatch_rule(request_simple)
            print(f"Успех (без агента)! ID: {res_simple.sip_dispatch_rule_id}")
        except Exception as e2:
            print(f"Минимальный вариант тоже не прошел: {e2}")

    await lk_api.aclose()

if __name__ == "__main__":
    asyncio.run(create_mango_rule())
