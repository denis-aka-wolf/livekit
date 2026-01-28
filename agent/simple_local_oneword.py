import logging

from livekit.agents import (
    JobContext,
    WorkerOptions,
    cli,
    Agent,
    AgentSession,
)
from livekit.plugins import openai, silero

log = logging.getLogger("simple-oneword-agent")


class OneWordAgent(Agent):
    def __init__(self) -> None:
        # LLM нам не нужен, инструкции просто для порядка
        super().__init__(
            instructions=(
                "Ты говоришь по-русски. "
                "Всегда отвечай ОДНИМ словом: «Привет». "
                "Не добавляй никаких других слов."
            )
        )

    async def on_participant_joined(self, participant) -> None:
        log.info("Участник подключился: %s", participant.identity)
        # Как только абонент зашёл в комнату — говорим одно слово
        await self.session.say("Привет")


async def entrypoint(ctx: JobContext):
    # Подключаемся к LiveKit (URL/KEY/SECRET придут из env)
    await ctx.connect()

    session = AgentSession(
        vad=silero.VAD.load(),   # локальный VAD
        llm=None,                # LLM не нужен, фраза фиксированная
        tts=openai.TTS(
            model="kokoro",                      # имя модели в Kokoro
            voice="af_heart",                   # голос, как в твоём curl
            base_url="http://localhost:8880/v1",  # OpenAI-совместимый endpoint
            api_key="dummy-key",                # Kokoro API-ключ не нужен, но плагину надо что-то передать
        ),
    )

    await session.start(
        agent=OneWordAgent(),
        room=ctx.room,
    )


if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            agent_name="simple-oneword-agent",  # ВАЖНО: этим именем будем вызывать через lk dispatch
        )
    )
