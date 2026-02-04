from __future__ import annotations

import asyncio
import logging
from dotenv import load_dotenv
import json
import os
import sys

from typing import Any

from livekit import rtc, api
from livekit.agents import (
    AgentSession,
    Agent,
    JobContext,
    function_tool,
    RunContext,
    get_job_context,
    cli,
    WorkerOptions,
    # RoomInputOptions,
    # RoomOptions,
)
from livekit.plugins import (
    openai,
#    cartesia,
    silero,
    # noise_cancellation,  # noqa: F401 - commented out to prevent cloud filters
)
from livekit.plugins.turn_detector.multilingual import MultilingualModel
# Добавляем родительскую директорию в sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from elaina_tts.elaina_tts import ElainaTTS

logger = logging.getLogger("elaina-inbound-worker")
logger.setLevel(logging.INFO)

def load_env_file(env_path):
    """Загрузка .env файла вручно для избежания проблем с символами возврата каретки"""
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()  # Удаляем все концевые пробелы, включая \r и \n
                if line and not line.startswith('#'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        # Удаляем потенциальные символы возврата каретки из значения
                        value = value.strip().rstrip('\r\n\t ')
                        os.environ[key] = value

# Загружаем .env файл вручно для предотвращения проблем с символами возврата каретки
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
load_env_file(env_path)


class InboundAgent(Agent):
    def __init__(self, *, phone_number: str = ""):
        # Словарь сопоставления номеров телефонов именам клиентов
        phone_to_name = {
            "79133888778": "Денис Сергеевич",
            "79955701443": "Денис",
            "79137296699": "Павел",
            "79831379240": "Артем"
        }
        # Определяем имя клиента по номеру телефона
        self.client_name = phone_to_name.get(phone_number, "Иван")
        
        # Читаем промпт из markdown файла
        prompt_template = self._load_prompt_template()
        # Подставляем переменные в промпт
        instructions = prompt_template.format(phone_number=phone_number, client_name=self.client_name)
        
        super().__init__(instructions=instructions)
        
        # keep reference to the participant for transfers
        self.participant: rtc.RemoteParticipant | None = None

        self.phone_number = phone_number
        
        # Флаг для отслеживания состояния завершения вызова
        self.call_ended = False
    
    def _load_prompt_template(self):
        """Загружает шаблон промпта из markdown файла"""
        
        # Определяем путь к файлу с промптом
        prompt_file_path = os.path.join(os.path.dirname(__file__), 'elaina-inbound-mango.md')
        
        # Читаем содержимое файла
        with open(prompt_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
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

    def set_participant(self, participant: rtc.RemoteParticipant):
        self.participant = participant

    async def hangup(self):
        """Вспомогательная функция для завершения вызова путем удаления комнаты."""

        job_ctx = get_job_context()
        await job_ctx.api.room.delete_room(
            api.DeleteRoomRequest(
                room=job_ctx.room.name,
            )
        )

    @function_tool()
    async def transfer_call(self, ctx: RunContext, transfer_to: str):
        """Перевести звонок оператору, после подтверждения пользователя."""

        if not transfer_to:
            return "cannot transfer call"

        logger.info(f"transferring call to {transfer_to}")

        #Перед передачей предупреждаем.
        await ctx.session.generate_reply(
            instructions="Сообщите пользователю, что вы собираетесь их перевести."
        )

        job_ctx = get_job_context()
        try:
            await job_ctx.api.sip.transfer_sip_participant(
                api.TransferSIPParticipantRequest(
                    room_name=job_ctx.room.name,
                    participant_identity=self.participant.identity,
                    transfer_to=f"tel:{transfer_to}",
                )
            )

            logger.info(f"transferred call to {transfer_to}")
        except Exception as e:
            logger.error(f"error transferring call: {e}")
            await ctx.session.generate_reply(
                instructions="there was an error transferring the call."
            )
            await self.hangup()

    @function_tool()
    async def end_call(self, ctx: RunContext):
        """Вызывается, когда пользователь хочет завершить вызов."""
        logger.info(f"ending the call for {self.participant.identity}")

        # Устанавливаем флаг завершения вызова
        self.call_ended = True

        # Останавливаем любые текущие и будущие попытки генерации речи
        try:
            current_speech = ctx.session.current_speech
            if current_speech:
                await current_speech.wait_for_playout()
        except Exception as e:
            logger.warning(f"Error waiting for speech playout: {e}")

        # Небольшая задержка для обеспечения завершения всех процессов
        await asyncio.sleep(0.5)

        await self.hangup()

    @function_tool()
    async def look_up_availability(
        self,
        ctx: RunContext,
        date: str,
    ):
        """Вызывается, когда пользователь запрашивает информацию 
            о наличии альтернативных вариантов записи на прием.

        Аргументы:
            date: Дата записи на прием, для которой необходимо проверить наличие свободных мест.
        """
        logger.info(
            f"looking up availability for {self.participant.identity} on {date}"
        )
        #await asyncio.sleep(3)
        return {
            "available_times": ["1pm", "2pm", "3pm"],
        }

    @function_tool()
    async def confirm_appointment(
        self,
        ctx: RunContext,
        date: str,
        time: str,
    ):
        """Вызывается, когда пользователь подтверждает свою запись на определенную дату.
        Используйте этот инструмент только в том случае, если вы уверены в дате и времени.

        Аргументы:
            date: Дата записи
            time: Время записи
        """
        logger.info(
            f"confirming appointment for {self.participant.identity} on {date} at {time}"
        )
        return "reservation confirmed"

    @function_tool()
    async def detected_answering_machine(self, ctx: RunContext):
        """Этот инструмент срабатывает, когда звонок поступает на голосовую почту.
        Используйте его ПОСЛЕ того, как услышите приветствие голосовой почты."""
        logger.info(f"detected answering machine for {self.participant.identity}")
        await self.hangup()


async def entrypoint(ctx: JobContext):
    logger.info(f"connecting to room {ctx.room.name}")
    await ctx.connect()

    # Для входящего вызова получаем информацию о SIP-участнике из метаданных
    sip_data = {}
    if ctx.job.metadata:
        try:
            sip_data = json.loads(ctx.job.metadata)
            logger.info(f"SIP metadata received: {sip_data}")
        except json.JSONDecodeError:
            logger.warning("Could not decode job metadata as JSON")
    
    # Получаем номер телефона из SIP-информации
    # Пытаемся получить номер из разных возможных полей
    phone_number = sip_data.get("sip_from_user") or sip_data.get("from_user") or sip_data.get("to_user", "unknown")
    
    # Если номер не найден в SIP-данных, пробуем извлечь из названия комнаты
    if phone_number == "unknown":
        import re
        room_phone_match = re.search(r'_(\d{11})_', ctx.room.name)
        if room_phone_match:
            phone_number = room_phone_match.group(1)
    
    logger.info(f"Phone number determined: {phone_number}")

    # Создаем агента с информацией о звонящем
    agent = InboundAgent(phone_number=phone_number)

    llama_model = os.getenv("LLAMA_MODEL", "qwen3-4b")
    llama_base_url = os.getenv("LLAMA_BASE_URL", "http://127.0.0.1:11434/v1")
    #aidar, baya, kseniya, xenia, eugene
    elaina_tts = ElainaTTS(speaker="baya", sample_rate=48000, num_channels=1)

    # Пайплайн
    session = AgentSession(
        #turn_detection=MultilingualModel(), # Отвечает за интеллектуальное определение конца фразы
        vad=silero.VAD.load(
            min_speech_duration=0.1,      # Минимальная длительность речи для детекции (увеличено для снижения нагрузки)
            min_silence_duration=0.5,     # Минимальная тишина перед завершением речи (увеличено для лучшей стабильности)
            prefix_padding_duration=0.2,   # Время предварительной задержки для более быстрой детекции
            #sample_rate=16000              # Частота дискретизации (поддерживаются только 8000 и 16000)
        ), # Определяет наличие человеческой речи в аудиопотоке
        # Главные ручки скорости:
        min_endpointing_delay=0.1, # Задержка после VAD (увеличено для более стабильной работы)
        min_interruption_words=2, # 0 или 1 для мгновенной реакции на перебивание
        #intent_threshold=0.9,       # Уверенность в завершении намерения
        stt=openai.STT(
            base_url="http://127.0.0.1:11435/v1",
            model=os.getenv("VOXBOX_HF_REPO_ID", "Systran/faster-whisper-small"),
            api_key="no-key-needed",
            language="ru",
        ),
        tts=elaina_tts,
        llm=openai.LLM(
            base_url=llama_base_url,
            model=llama_model,
            api_key="no-key-needed",
            timeout=5.0,  # Увеличенный таймаут для генерации ответа
            max_retries=3,  # Количество попыток при ошибках
        ),
    )

    # Обработчик для всех метрик
    from livekit.agents import metrics, MetricsCollectedEvent
    
    @session.on("metrics_collected")
    def _on_metrics_collected(ev: MetricsCollectedEvent):
        # Логируем все метрики
        #metrics.log_metrics(ev.metrics)
        
        # Также можем логировать каждую метрику отдельно
        metric_type = type(ev.metrics).__name__
        if metric_type == "EOUMetrics":
            logger.info(f"[VAD] Конец фразы найден через: {ev.metrics.end_of_utterance_delay:.2f}с")
        elif metric_type == "STTMetrics":
            logger.info(f"[STT] Распознано за: {ev.metrics.duration:.2f}с")
        elif metric_type == "LLMMetrics":
            logger.info(f"[LLM] Время до первого слова (TTFT): {ev.metrics.ttft:.2f}с")
            logger.info(f"[LLM] Общая генерация: {ev.metrics.duration:.2f}с")
        elif metric_type == "TTSMetrics":
            logger.info(f"[TTS] Время до начала звука (TTFB): {ev.metrics.ttfb:.2f}с")
        
    # Прогрев промпта (Prompt Warmup) - выполняем холостой вызов LLM для создания кэша
    try:
        # Читаем промпт из markdown файла, как это делает сам агент
        prompt_template = agent._load_prompt_template()
        # Подставляем переменные в промпт
        warmup_prompt = prompt_template.format(phone_number=phone_number, client_name=agent.client_name)
        
        # Выполняем холостой вызов для прогрева модели
        await session.llm.chat(
            history=[openai.ChatMessage(role="system", content=warmup_prompt)],
            temperature=0.7
        )
        logger.info("Prompt warmup completed successfully")
    except Exception as e:
        logger.warning(f"Prompt warmup failed: {e}")
    
    # Начинаем сессию агента
    await session.start(agent=agent, room=ctx.room)

    # Ждем подключения участника (SIP-участник будет автоматически добавлен при входящем вызове)
    participant = await ctx.wait_for_participant()  # Ожидаем первого участника
    logger.info(f"participant joined: {participant.identity}")

    # Если номер телефона не был определен ранее, пробуем извлечь из идентификатора участника
    if agent.phone_number == "unknown":
        import re
        participant_identity = participant.identity
        if participant_identity and participant_identity.startswith('sip_'):
            phone_number = participant_identity[4:]  # Убираем префикс 'sip_'
            # Обновляем имя клиента в агенте
            phone_to_name = {
                "79133888778": "Денис Сергеевич",
                "79955701443": "Денис",
                "79137296699": "Павел",
                "79831379240": "Артем"
            }
            agent.client_name = phone_to_name.get(phone_number, "Иван")
            agent.phone_number = phone_number

    # Устанавливаем участника в агенте
    agent.set_participant(participant)

    # Сразу говорим фразу приветствия
    await session.say(f'<prosody rate="175%"> Здравствуйте {agent.client_name}, медицинский центр СМИТРА. Меня зовут Елена, слушаю вас? </prosody>')



if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            agent_name="elaina-inbound-mango",
            job_memory_warn_mb=8000, 
        )
    )

