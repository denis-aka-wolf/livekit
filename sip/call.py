import asyncio
import os
import sys
import logging
from dotenv import load_dotenv
from livekit import api

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)

load_dotenv()

logger = logging.getLogger("make-call")
logger.setLevel(logging.INFO)

room_name = "elaina"
agent_name = "elaina"
outbound_trunk_id = os.getenv("SIP_OUTBOUND_TRUNK_ID")

async def make_call(phone_number):
    lkapi = api.LiveKitAPI(
        url=os.getenv("LIVEKIT_URL"),
        api_key=os.getenv("LIVEKIT_API_KEY"),
        api_secret=os.getenv("LIVEKIT_API_SECRET"),
    )

    logger.info(f"Создание правила для {agent_name} в канале {room_name}")
    dispatch = await lkapi.agent_dispatch.create_dispatch(
        api.CreateAgentDispatchRequest(
            agent_name=agent_name, room=room_name, metadata=phone_number
        )
    )
    logger.info(f"Создано правило: {dispatch}")

    if not outbound_trunk_id or not outbound_trunk_id.startswith("ST_"):
        logger.error("❌ SIP_OUTBOUND_TRUNK_ID не верный")
        return

    logger.info(f"Набираем номер телефона {phone_number} в канале {room_name}")

    try:
        sip_participant = await lkapi.sip.create_sip_participant(
            api.CreateSIPParticipantRequest(
                room_name=room_name,
                sip_trunk_id=outbound_trunk_id,
                sip_call_to=phone_number,
                participant_identity="phone_user",
            )
        )
        logger.info(f"Создан участник SIP: {sip_participant}")
    except Exception as e:
        logger.error(f"❌ Ошибка создания SIP участника: {e}")
    
    asyncio.sleep(30)
    await lkapi.aclose()

async def main():
    phone_number = os.getenv("DESTINATION_NUMBER")
    await make_call(phone_number)

if __name__ == "__main__":
    asyncio.run(main())