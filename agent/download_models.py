#!/usr/bin/env python3
"""Скрипт для загрузки необходимых моделей для работы агента."""

import os
from pathlib import Path
from huggingface_hub import hf_hub_download


def download_turn_detector_model():
    """Загрузка модели для детектора речи."""
    print("Загрузка модели turn detector...")
    
    # Папка для хранения моделей
    models_dir = Path.home() / ".cache" / "livekit" / "plugins" / "turn-detector"
    models_dir.mkdir(parents=True, exist_ok=True)
    
    # Загружаем модель model_q8.onnx
    try:
        hf_hub_download(
            repo_id="livekit-plugins/models",
            filename="turn-detector/model_q8.onnx",
            local_dir=models_dir,
            local_dir_use_symlinks=False
        )
        print(f"✓ Модель успешно загружена в {models_dir}")
        return True
    except Exception as e:
        print(f"✗ Ошибка при загрузке модели: {e}")
        return False


def download_silero_vad_model():
    """Загрузка модели Silero VAD."""
    print("Загрузка модели Silero VAD...")
    
    # Папка для хранения моделей
    models_dir = Path.home() / ".cache" / "livekit" / "plugins" / "silero-vad"
    models_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        hf_hub_download(
            repo_id="snakers4/silero-vad",
            filename="silero_vad.onnx",
            local_dir=models_dir,
            local_dir_use_symlinks=False
        )
        print(f"✓ Модель Silero VAD успешно загружена в {models_dir}")
        return True
    except Exception as e:
        print(f"✗ Ошибка при загрузке модели Silero VAD: {e}")
        return False


def main():
    print("Загрузка необходимых моделей для LiveKit агента...")
    print("="*50)
    
    success_count = 0
    
    if download_turn_detector_model():
        success_count += 1
    
    if download_silero_vad_model():
        success_count += 1
    
    print("="*50)
    if success_count > 0:
        print(f"✓ Загружено {success_count} моделей")
        print("Теперь вы можете запустить агента.")
    else:
        print("✗ Не удалось загрузить ни одной модели")


if __name__ == "__main__":
    main()