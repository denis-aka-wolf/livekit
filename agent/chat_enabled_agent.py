import asyncio
import logging
import os
from dotenv import load_dotenv

# Важно: используем AgentSession для работы с Realtime/LLM
from livekit.agents import AgentServer, JobContext, cli
from livekit.plugins import openai
import livekit.rtc as rtc

logger = logging.getLogger("chat-enabled-worker")
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

@server.rtc_session()
async def entrypoint(ctx: JobContext):
    # Подключаемся к любой комнате без фильтрации
    logger.info(f"Агент подключается к комнате: {ctx.room.name}")
    
    # Правильная настройка LLM для локального сервера (llama.cpp)
    # Используем OpenAI плагин, так как llama.cpp имитирует его API
    llm = openai.LLM(
        base_url=os.getenv("LLAMA_BASE_URL", "http://localhost:11434/v1"),
        api_key="fake-key", # локальные серверы обычно не требуют ключ
        model=os.getenv("LLAMA_MODEL", "qwen3-4b")
    )
    
    logger.info(f"Подключено к комнате: {ctx.room.name}")
    logger.info(f"Количество участников при подключении агента: {ctx.room.num_participants}")
    
    # Подключаемся к комнате
    await ctx.connect()
    logger.info(f"Агент успешно подключен к RTC сессии")
    
    # Логируем информацию о текущих участниках после подключения
    logger.info(f"Информация об участниках после подключения агента: количество участников {ctx.room.num_participants}")
    
    # Создаем словарь для отслеживания участников
    participants_dict = {}
    
    # Регистрируем обработчики для отслеживания участников
    def on_participant_connected(participant):
        participants_dict[participant.sid] = participant
        logger.info(f"Участник подключился: {participant.identity}, SID: {participant.sid}")
    
    def on_participant_disconnected(participant):
        if participant.sid in participants_dict:
            del participants_dict[participant.sid]
        logger.info(f"Участник отключился: {participant.identity}, SID: {participant.sid}")
    
    # Подписываемся на события участников
    ctx.room.on("participant_connected", on_participant_connected)
    ctx.room.on("participant_disconnected", on_participant_disconnected)
    
    # Логируем уже подключенных участников
    logger.info("Уже подключенные участники:")
    # Для получения текущих участников нужно использовать события, так как direct access недоступен

    # Регистрируем обработчик получения данных (включая чат-сообщения)
    logger.info("Настройка обработчика получения данных...")
    def on_data_received_sync(data_packet: rtc.DataPacket):
        logger.info(f"Получен пакет данных - Тип: {type(data_packet)}, Длина данных: {len(data_packet.data) if hasattr(data_packet, 'data') and data_packet.data else 0}")
        logger.info(f"Информация об участнике: {data_packet.participant.identity if data_packet.participant else 'Нет'}")
        logger.info(f"Топик: {getattr(data_packet, 'topic', 'Без топика')}")
        # Создаем асинхронную задачу для обработки данных
        asyncio.create_task(handle_data_received(data_packet))
    
    async def handle_data_received(data_packet: rtc.DataPacket):
        try:
            message_content = data_packet.data.decode('utf-8')
            sender_identity = data_packet.participant.identity if data_packet.participant else 'server'
            topic_info = getattr(data_packet, 'topic', 'Без топика')
            
            logger.info(f"Получено сообщение чата: {message_content} от {sender_identity}, топик: {topic_info}")
            
            # Попробуем распарсить JSON-сообщение, если оно в формате JSON
            import json
            try:
                parsed_message = json.loads(message_content)
                if isinstance(parsed_message, dict) and 'message' in parsed_message:
                    actual_message = parsed_message['message']
                else:
                    actual_message = message_content
            except json.JSONDecodeError:
                actual_message = message_content
            
            # Обрабатываем сообщение и отправляем ответ
            response = f"Агент получил: {actual_message}"
            
            # Отправляем ответ как надежное сообщение данных
            logger.info(f"Попытка отправить ответ: {response}")
            # Сначала попробуем определить топик исходного сообщения, чтобы ответить в тот же топик
            original_topic = getattr(data_packet, 'topic', 'lk-chat-topic')  # По умолчанию используем топик, который виден в логах
            logger.info(f"Ответ на сообщение с топиком: {original_topic}")
            try:
                # Попробуем отправить как обычное сообщение данных с оригинальным топиком
                await ctx.agent.publish_data(
                    response,
                    reliable=True,
                    topic=original_topic
                )
                logger.info(f"Успешно отправлен ответ через publish_data с топиком '{original_topic}': {response}")
            except Exception as send_error:
                logger.error(f"Не удалось отправить сообщение через канал данных с топиком '{original_topic}': {send_error}")
                # Попробуем стандартный топик чата
                try:
                    await ctx.agent.publish_data(
                        response,
                        reliable=True,
                        topic="lk-chat-topic"  # Используем топик, который видели в логах браузера
                    )
                    logger.info(f"Успешно отправлен ответ через publish_data с топиком 'lk-chat-topic': {response}")
                except Exception as alt_error:
                    logger.error(f"Не удалось отправить через publish_data с топиком 'lk-chat-topic': {alt_error}")
                    # Попробуем отправить без топика
                    try:
                        await ctx.agent.publish_data(
                            response,
                            reliable=True
                        )
                        logger.info(f"Успешно отправлен ответ через publish_data без топика: {response}")
                    except Exception as no_topic_error:
                        logger.error(f"Не удалось отправить через publish_data без топика: {no_topic_error}")
                        # Попробуем использовать send_text
                        try:
                            await ctx.agent.send_text(response)
                            logger.info(f"Успешно отправлен ответ через send_text: {response}")
                        except Exception as fallback_error:
                            logger.error(f"Метод send_text также не удался: {fallback_error}")
                            # Финальная попытка - использовать метод комнаты
                            try:
                                await ctx.room.local_participant.publish_data(
                                    response,
                                    topic="lk-chat-topic"
                                )
                                logger.info(f"Успешно отправлен ответ через room.local_participant.publish_data с топиком 'lk-chat-topic': {response}")
                            except Exception as room_method_error:
                                logger.error(f"Метод комнаты также не удался: {room_method_error}")
            
        except Exception as e:
            logger.error(f"Ошибка при обработке полученных данных: {e}", exc_info=True)
    
    # Регистрируем синхронный обработчик
    ctx.room.on("data_received", on_data_received_sync)
    logger.info("Обработчик получения данных зарегистрирован")

    # Отправляем приветственное сообщение при подключении
    logger.info("Попытка отправить приветственное сообщение...")
    try:
        await ctx.agent.publish_data(
            "Агент подключен к чату и готов к работе!",
            reliable=True,
            topic="lk-chat-topic"  # Используем топик, который ожидает клиент
        )
        logger.info("Успешно отправлено приветственное сообщение через agent.publish_data с топиком lk-chat-topic")
    except Exception as e:
        logger.error(f"Не удалось отправить приветственное сообщение через agent.publish_data с топиком lk-chat-topic: {e}")
        # Альтернативный способ отправки
        try:
            await ctx.agent.publish_data(
                "Агент подключен к чату и готов к работе!",
                reliable=True
            )
            logger.info("Успешно отправлено приветственное сообщение через agent.publish_data без топика")
        except Exception as e2:
            logger.error(f"Не удалось отправить приветственное сообщение через agent.publish_data без топика: {e2}")
            # Еще один альтернативный способ
            try:
                await ctx.agent.send_text("Агент подключен к чату и готов к работе!")
                logger.info("Успешно отправлено приветственное сообщение через agent.send_text")
            except Exception as e3:
                logger.error(f"Все методы агента для отправки приветственного сообщения не удалась: {e3}")
                # Попробуем использовать метод комнаты напрямую
                try:
                    await ctx.room.local_participant.publish_data(
                        "Агент подключен к чату и готов к работе!",
                        topic="lk-chat-topic"
                    )
                    logger.info("Успешно отправлено приветственное сообщение через room.local_participant.publish_data с топиком lk-chat-topic")
                except Exception as room_method_error:
                    logger.error(f"Все методы для отправки приветственного сообщения не удалась: {room_method_error}")

    # Ждем пока комната не станет недоступной
    logger.info("Начало основного цикла мониторинга комнаты")
    try:
        while ctx.room.isconnected():
            logger.info(f"Комната активна: {ctx.room.name}, участников: {ctx.room.num_participants}")
            # Логируем информацию о количестве участников
            logger.info(f"  Количество участников по данным комнаты: {ctx.room.num_participants}")
            await asyncio.sleep(30)
    except Exception as e:
        logger.error(f"Ошибка в основном цикле: {e}", exc_info=True)
    finally:
        logger.info("Агент отключается от комнаты")
        
        # Отписываемся от событий
        ctx.room.off("participant_connected", on_participant_connected)
        ctx.room.off("participant_disconnected", on_participant_disconnected)

if __name__ == "__main__":
    # cli.run_app сам подтянет LIVEKIT_API_KEY и SECRET из среды
    cli.run_app(server)