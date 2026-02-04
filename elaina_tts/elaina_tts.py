import os
import asyncio
import torch
import numpy as np
from livekit.agents import tts
from livekit import rtc

class ElainaTTS(tts.TTS):
    def __init__(
        self,
        speaker: str = "baya",  #aidar, baya, kseniya, xenia, eugene
        sample_rate: int = 48000,
        num_channels: int = 1,
        set_num_threads: int = 2,
    ):
        super().__init__(
            capabilities=tts.TTSCapabilities(streaming=False),
            sample_rate=sample_rate,
            num_channels=num_channels
        )
        self._speaker = speaker
        self._sample_rate = sample_rate
        self._num_channels = num_channels
        
        model_name = "elaina.pt"
        # Определяем путь к модели в той же папке, где этот скрипт
        current_dir = os.path.dirname(os.path.abspath(__file__))
        model_path = os.path.join(current_dir, model_name)

        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Файл модели не найден: {model_path}")

        # Оптимизация потоков для снижения нагрузки на CPU
        torch.set_num_threads(set_num_threads)
        device = torch.device("cpu")
        package = torch.package.PackageImporter(model_path)
        self._model = package.load_pickle("tts_models", "model")
        self._model.to(device)
        
        # Загрузка через JIT (решает проблему с импортами package)
        #self.model = torch.jit.load(model_path, map_location=device)
        #self.model.eval()

        # Другой вариант
        #self._model = importer.load_pickle("tts_models", "model")
        #self._model.to(torch.device("cpu"))
        #self._model.eval()

    # Метод для смены спикера в процессе работы
    def update_options(self, speaker: str):
        self._speaker = speaker

    def synthesize(self, text: str, *, conn_options=None, **kwargs) -> tts.ChunkedStream:
        from livekit.agents import APIConnectOptions
        if conn_options is None:
            conn_options = APIConnectOptions(max_retry=0)
        return ElainaStream(tts=self, input_text=text, conn_options=conn_options)

class ElainaStream(tts.ChunkedStream):
    def __init__(self, *, tts: ElainaTTS, input_text: str, conn_options):
        # Инициализируем базовый класс
        super().__init__(tts=tts, input_text=input_text, conn_options=conn_options)
        self._tts = tts
        self._input_text = input_text

    async def _run(self, output_emitter: "tts.AudioEmitter") -> None:
        """Реализация абстрактного метода _run"""
        print(f"TTS: Начало синтеза речи для текста: '{self._input_text[:50]}...'")  # первые 50 символов для отладки
        
        # Инициализируем AudioEmitter перед использованием
        output_emitter.initialize(
            request_id="req_" + str(hash(self._input_text))[:8],  # генерируем уникальный ID запроса
            sample_rate=self._tts._sample_rate,
            num_channels=self._tts._num_channels,
            mime_type="audio/pcm",
            stream=False,
        )
        
        def _render():
            tensor = self._tts._model.apply_tts(
                text=self._input_text,
                speaker=self._tts._speaker,
                sample_rate=self._tts._sample_rate
            )
            audio_data = (tensor.numpy() * 32767).astype(np.int16)
            return audio_data.tobytes()

        # Генерируем аудио в отдельном потоке
        pcm_bytes = await asyncio.to_thread(_render)
        
        print(f"Синтезировано {len(pcm_bytes)} байт аудио")

        # Отправляем синтезированный аудио через emitter
        output_emitter.push(pcm_bytes)
        output_emitter.flush()  # Убедиться, что фрейм отправлен
        print("Отправлен аудиофрейм")
