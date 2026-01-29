import os
import torch
import io
from pathlib import Path
from typing import Optional



class TTS:
    """
    Локальный клиент для Silero TTS v5 (без сервера).
    
    Параметры:
    - model_path: путь к файлу модели (по умолчанию 'silero_v5_ru.pt' в текущем каталоге)
    - speaker: голос (например, 'baya', 'kseniya' и др.)
    - sample_rate: частота дискретизации (48000 — нативное качество модели)
    """

    def __init__(
        self,
        model_path: str = None,
        speaker: str = "baya",
        sample_rate: int = 48000
    ):
        # Если путь не указан — используем текущий каталог
        if model_path is None:
            self.model_path = Path("silero_v5_ru.pt").resolve()
        else:
            self.model_path = Path(model_path).resolve()

        self.speaker = speaker
        self.sample_rate = sample_rate
        self.model = None
        
        # Инициализация при создании экземпляра
        self._load_model()

    def _load_model(self):
        """Загружает модель Silero TTS v5 локально."""
        device = torch.device("cpu")
        torch.set_num_threads(4)

        # Убедимся, что путь к модели — абсолютный
        model_path = self.model_path

        # Если модель не скачана — скачиваем в указанный каталог
        if not model_path.is_file():
            print(f"Скачиваю модель Silero TTS v5 в {model_path}...")
            try:
                torch.hub.download_url_to_file(
                    "https://models.silero.ai/models/tts/ru/v5_ru.pt",
                    str(model_path)
                )
            except Exception as e:
                raise RuntimeError(f"Ошибка скачивания модели: {e}")

        # Загружаем модель
        try:
            package = torch.package.PackageImporter(str(model_path))
            self.model = package.load_pickle("tts_models", "model")
            self.model.to(device)
            print(f"Модель Silero TTS v5 загружена из {model_path}.")
        except Exception as e:
            raise RuntimeError(f"Ошибка загрузки модели: {e}")

    def synthesize(self, text: str) -> Optional[bytes]:
        """
        Синтезирует речь из текста и возвращает аудио в формате WAV (bytes).
        
        Параметры:
        - text: входной текст для синтеза
        
        Возвращает:
        - bytes: аудиоданные в формате WAV или None при ошибке
        """
        if not self.model:
            print("Модель не загружена!")
            return None

        try:
            # Синтез аудио
            audio_paths = self.model.save_wav(
                text=text,
                speaker=self.speaker,
                sample_rate=self.sample_rate
            )
            
            # Читаем WAV-файл в bytes
            with open(audio_paths[0], "rb") as f:
                wav_data = f.read()
            
            # Удаляем временный файл
            os.remove(audio_paths[0])
            
            return wav_data

        except Exception as e:
            print(f"Ошибка синтеза TTS: {e}")
            return None

    def save_to_file(self, text: str, filename: str) -> bool:
        """
        Синтезирует речь и сохраняет в файл WAV.
        
        Параметры:
        - text: текст для синтеза
        - filename: путь к файлу для сохранения
        
        Возвращает:
        - bool: True, если сохранение прошло успешно
        """
        audio_data = self.synthesize(text)
        if audio_data:
            try:
                with open(filename, "wb") as f:
                    f.write(audio_data)
                return True
            except Exception as e:
                print(f"Ошибка при сохранении файла: {e}")
                return False
        return False
