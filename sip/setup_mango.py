import asyncio
from livekit import api

URL = "http://158.160.2.82:7880"
API_KEY = ""
API_SECRET = ""
EXISTING_INBOUND_TRUNK_ID = "ST_SbAbWDDUgUtP"

async def setup_mango_sip():
    lk_api = api.LiveKitAPI(URL, API_KEY, API_SECRET)
    sip_client = lk_api.sip

    print(f"--- Используем входящий транк: {EXISTING_INBOUND_TRUNK_ID} ---")
    
    print("\n--- Создание Dispatch Rule ---")
    try:
        # В версии 2026 настройки агентов передаются внутри SIPDispatchRuleInfo
        # Но сама структура Rule остается прежней
        request = api.CreateSIPDispatchRuleRequest(
            rule=api.SIPDispatchRuleInfo(
                name="mango-dispatch",
                trunk_ids=[EXISTING_INBOUND_TRUNK_ID],
                rule=api.SIPDispatchRule(
                    dispatch_rule_individual=api.SIPDispatchRuleIndividual(
                        room_prefix="mango_"
                    )
                ),
                # Если SIPRoomConfig не найден, попробуйте передать параметры напрямую
                # В некоторых версиях 2026 года используется metadata или доп. поля
                # Для теста сначала попробуем БЕЗ блока room_config, чтобы убедиться в работе правила
            )
        )
        
        dispatch_rule = await sip_client.create_dispatch_rule(request)
        print(f"Правило создано! ID: {dispatch_rule.sip_dispatch_rule_id}")
        
    except Exception as e:
        print(f"Ошибка при создании Dispatch Rule: {e}")

    await lk_api.aclose()

if __name__ == "__main__":
    asyncio.run(setup_mango_sip())
