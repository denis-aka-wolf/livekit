#!/usr/bin/env python3
"""
Custom Russian TTS Integration for LiveKit Agents
Integrates the Kokoro Russian TTS model with LiveKit agents
"""

import asyncio
import io
import logging
from typing import AsyncIterator, Optional
import tempfile
import os
import wave
import threading
import queue

import numpy as np
import torch
from livekit import rtc
from livekit.agents import tts
from livekit.agents.utils import AudioBuffer, merge_frames

from kokoro_ru.inference import KokoroTTS


logger = logging.getLogger("kokoro_tts")


class KokoroTTSService(tts.TTSService):
    """Russian TTS service using Kokoro model for LiveKit agents"""
    
    def __init__(self, model_path: str = "./kokoro_russian_model", device: str = None, **kwargs):
        super().__init__()
        self._model_path = model_path
        self._device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        
        # Initialize the Kokoro TTS model
        try:
            self._tts_model = KokoroTTS(
                model_dir=model_path,
                device=self._device,
                vocoder_type="hifigan"
            )
            logger.info(f"Kokoro TTS model loaded successfully from {model_path}")
        except Exception as e:
            logger.error(f"Failed to load Kokoro TTS model: {e}")
            raise

    async def synthesize(self, text: str) -> AsyncIterator[tts.SynthesizedAudio]:
        """Synthesize audio from text using Kokoro TTS model"""
        try:
            # Create a temporary file for audio output
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_path = temp_file.name
            
            # Synthesize audio using Kokoro TTS (this runs synchronously)
            audio_tensor = await asyncio.get_event_loop().run_in_executor(
                None, 
                lambda: self._tts_model.text_to_speech(text, temp_path)
            )
            
            # Read the generated audio file
            if os.path.exists(temp_path):
                with open(temp_path, 'rb') as f:
                    audio_data = f.read()
                
                # Parse WAV file to get audio properties
                wav_buffer = io.BytesIO(audio_data)
                with wave.open(wav_buffer, 'rb') as wav_file:
                    sample_rate = wav_file.getframerate()
                    channels = wav_file.getnchannels()
                    width = wav_file.getsampwidth()
                    
                    # Read audio frames
                    raw_frames = wav_file.readframes(wav_file.getnframes())
                    
                    # Convert to numpy array
                    if width == 2:  # 16-bit
                        audio_array = np.frombuffer(raw_frames, dtype=np.int16)
                    elif width == 4:  # 32-bit
                        audio_array = np.frombuffer(raw_frames, dtype=np.int32)
                    else:
                        audio_array = np.frombuffer(raw_frames, dtype=np.uint8)
                    
                    # Convert to float32 normalized [-1, 1]
                    if width == 2:
                        audio_float = audio_array.astype(np.float32) / 32768.0
                    elif width == 4:
                        audio_float = audio_array.astype(np.float32) / 2147483648.0
                    else:
                        audio_float = (audio_array.astype(np.float32) - 128.0) / 128.0
                    
                    # If stereo, convert to mono by averaging
                    if channels > 1:
                        audio_float = audio_float.reshape(-1, channels).mean(axis=1)
                    
                    # Convert to 16-bit PCM
                    audio_pcm = (audio_float * 32767).astype(np.int16)
                    
                    # Create audio frame
                    audio_frame = rtc.AudioFrame(
                        data=audio_pcm.tobytes(),
                        sample_rate=sample_rate,  # Should be 22050 according to Kokoro config
                        num_channels=1,
                        samples_per_channel=len(audio_pcm)
                    )
                    
                    yield tts.SynthesizedAudio(
                        text=text,
                        audio=audio_frame
                    )
                
                # Clean up temporary file
                os.unlink(temp_path)
            else:
                logger.error(f"Generated audio file not found: {temp_path}")
                raise Exception("TTS synthesis failed - no audio file generated")
                
        except Exception as e:
            logger.error(f"Error synthesizing audio for text '{text}': {e}")
            raise


class KokoroTTSOptions:
    """Options for configuring Kokoro TTS"""
    
    def __init__(self, 
                 model_path: str = "./kokoro_russian_model",
                 device: str = None,
                 voice: str = "default",
                 speed: float = 1.0,
                 pitch: float = 1.0,
                 intonation: float = 1.0):
        self.model_path = model_path
        self.device = device
        self.voice = voice
        self.speed = speed
        self.pitch = pitch
        self.intonation = intonation


def create_default_tts(options: Optional[KokoroTTSOptions] = None) -> KokoroTTSService:
    """Create a default Kokoro TTS service instance"""
    if options is None:
        options = KokoroTTSOptions()
    
    return KokoroTTSService(
        model_path=options.model_path,
        device=options.device
    )


# Alternative wrapper that could support Silero TTS if available
class SileroTTSService(tts.TTSService):
    """Silero TTS service with Russian language support and configurable parameters"""
    
    def __init__(self, 
                 model_id: str = "silero_tts_ru",
                 voice: str = "kseniya",  # Default Russian voice
                 speed: float = 1.0,
                 speaker_embedding: Optional[str] = None,
                 **kwargs):
        super().__init__()
        self._model_id = model_id
        self._voice = voice
        self._speed = speed
        self._speaker_embedding = speaker_embedding
        
        # Try to import silero TTS
        try:
            import torch
            self._torch = torch
            # Load Silero TTS model
            self._model, self._symbols, self._sample_rate, self._vox = self._load_model()
        except ImportError:
            logger.warning("Silero TTS not available, falling back to Kokoro TTS")
            # Fallback to Kokoro TTS
            self._use_kokoro = True
            self._kokoro_service = KokoroTTSService(**kwargs)
        except Exception as e:
            logger.error(f"Error initializing Silero TTS: {e}")
            raise
    
    def _load_model(self):
        """Load the Silero TTS model"""
        # This is a simplified version - actual Silero TTS integration would be more complex
        try:
            import silero_tts  # This package might not exist in this form
            model, symbols, sample_rate, vox = silero_tts.load_model(
                model_id=self._model_id,
                device="cpu"  # Use CPU by default for compatibility
            )
            return model, symbols, sample_rate, vox
        except ImportError:
            # If silero_tts package is not available, we'll need to use an alternative approach
            raise ImportError("Silero TTS package not available")

    async def synthesize(self, text: str) -> AsyncIterator[tts.SynthesizedAudio]:
        """Synthesize audio from text using Silero TTS"""
        if hasattr(self, '_use_kokoro') and self._use_kokoro:
            # Use Kokoro TTS as fallback
            async for audio in self._kokoro_service.synthesize(text):
                yield audio
        else:
            # Use actual Silero TTS
            try:
                # Generate audio using Silero TTS
                audio = self._model.apply_tts(
                    text=text,
                    speaker=self._voice,
                    sample_rate=self._sample_rate,
                    put_accent=True,
                    put_yo=True
                )
                
                # Convert to required format
                audio_int16 = (audio * 32767).astype(np.int16)
                
                audio_frame = rtc.AudioFrame(
                    data=audio_int16.tobytes(),
                    sample_rate=self._sample_rate,
                    num_channels=1,
                    samples_per_channel=len(audio_int16)
                )
                
                yield tts.SynthesizedAudio(
                    text=text,
                    audio=audio_frame
                )
            except Exception as e:
                logger.error(f"Error synthesizing audio with Silero TTS: {e}")
                raise


def create_silero_tts(options: Optional[dict] = None) -> SileroTTSService:
    """Create a Silero TTS service instance with configurable options"""
    if options is None:
        options = {}
    
    return SileroTTSService(**options)