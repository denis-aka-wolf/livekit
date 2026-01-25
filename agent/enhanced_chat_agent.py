import asyncio
import logging
import os
from dotenv import load_dotenv
import json

# Важно: используем AgentSession для работы с Realtime/LLM
from livekit.agents import AgentServer, JobContext, cli
from livekit.plugins import openai
import livekit.rtc as rtc

logger = logging.getLogger("enhanced-chat-agent")
logger.setLevel(logging.INFO)

def load_env_file(env_path):
    """Загрузка .env файла вручную для избежания проблем с символами возврата каретки"""
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

# Загружаем .env файл вручную для предотвращения проблем с символами возврата каретки
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
load_env_file(env_path)

server = AgentServer()

class ChatAgent:
    def __init__(self, ctx: JobContext):
        self.ctx = ctx
        self.chat_history = []
        self.is_processing = False
        
    def add_message_to_history(self, sender, message, message_type="user"):
        """Добавить сообщение в историю чата"""
        self.chat_history.append({
            "sender": sender,
            "message": message,
            "type": message_type,
            "timestamp": asyncio.get_event_loop().time()
        })
        # Ограничиваем историю последними 50 сообщениями
        if len(self.chat_history) > 50:
            self.chat_history = self.chat_history[-50:]

    async def send_chat_message(self, message: str, destination_identities=None, topic="chat"):
        """Отправить сообщение в чат"""
        try:
            await self.ctx.agent.send_text(
                message,
                destination_identities=destination_identities,
                topic=topic
            )
            logger.info(f"Sent chat message: {message[:50]}...")
            return True
        except Exception as e:
            logger.error(f"Failed to send chat message: {e}")
            return False

    async def process_user_message(self, message: str, sender_identity: str = None):
        """Обработать входящее сообщение от пользователя"""
        if self.is_processing:
            await self.send_chat_message("Подождите, я еще обрабатываю предыдущее сообщение.", 
                                       destination_identities=[sender_identity] if sender_identity else None)
            return

        self.is_processing = True
        try:
            # Добавляем сообщение в историю
            self.add_message_to_history(sender_identity or "unknown", message, "user")
            
            # Отправляем сообщение о том, что агент думает
            await self.send_chat_message("Обрабатываю ваше сообщение...", 
                                       destination_identities=[sender_identity] if sender_identity else None,
                                       topic="typing")

            # Здесь можно интегрировать LLM для генерации ответа
            # Для примера просто эхо-ответ
            response = f"Вы сказали: {message}"
            
            # Добавляем ответ в историю
            self.add_message_to_history("agent", response, "agent")
            
            # Отправляем ответ пользователю
            await self.send_chat_message(response, 
                                       destination_identities=[sender_identity] if sender_identity else None,
                                       topic="response")
                                       
        except Exception as e:
            logger.error(f"Error processing user message: {e}")
            await self.send_chat_message("Произошла ошибка при обработке вашего сообщения.",
                                       destination_identities=[sender_identity] if sender_identity else None)
        finally:
            self.is_processing = False

@server.rtc_session()
async def entrypoint(ctx: JobContext):
    # Фильтр комнаты
    if ctx.room.name != "my_room":
        logger.info(f"Skipping room {ctx.room.name}")
        return 

    # Создаем экземпляр агента
    chat_agent = ChatAgent(ctx)
    
    # Правильная настройка LLM для локального сервера (llama.cpp)
    # Используем OpenAI плагин, так как llama.cpp имитирует его API
    llm = openai.LLM(
        base_url=os.getenv("LLAMA_BASE_URL", "http://localhost:11434/v1"),
        api_key="fake-key", # локальные серверы обычно не требуют ключ
        model=os.getenv("LLAMA_MODEL", "qwen3-4b")
    )
    
    logger.info(f"Connected to room: {ctx.room.name}")
    
    # Подключаемся к комнате
    await ctx.connect()

    # Регистрируем обработчик получения данных (включая чат-сообщения)
    @ctx.room.on("data_received")
    async def on_data_received(data_packet: rtc.DataPacket):
        try:
            message_content = data_packet.data.decode('utf-8')
            sender_identity = data_packet.participant.identity if data_packet.participant else 'server'
            
            logger.info(f"Received chat message: {message_content} from {sender_identity}")
            
            # Обрабатываем сообщение
            await chat_agent.process_user_message(message_content, sender_identity)
            
        except Exception as e:
            logger.error(f"Error handling received data: {e}")

    # Пример отправки приветственного сообщения при подключении
    await chat_agent.send_chat_message("Агент подключен к чату и готов к работе!", topic="welcome")

    # Цикл агента - выполнение периодических задач
    while True:
        # Логируем количество участников
        logger.info(f"Number of participants in room: {ctx.room.num_participants}")
        
        # Можно добавить логику периодического оповещения
        # await chat_agent.send_chat_message(f"Комната активна, участников: {ctx.room.num_participants}", topic="status")
        
        await asyncio.sleep(60)

if __name__ == "__main__":
    # cli.run_app сам подтянет LIVEKIT_API_KEY и SECRET из среды
    cli.run_app(server)