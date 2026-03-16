"""Audio I/O — microphone capture, speech-to-text, text-to-speech, and voice activity detection."""

from src.audio.capture import AudioCapture
from src.audio.transcribe import transcribe, transcribe_file, TranscriptionResult
from src.audio.tts import speak, speak_async, save_speech, list_voices, set_voice, set_rate
from src.audio.vad import detect_speech, is_speaking

__all__ = [
    "AudioCapture",
    "transcribe",
    "transcribe_file",
    "TranscriptionResult",
    "speak",
    "speak_async",
    "save_speech",
    "list_voices",
    "set_voice",
    "set_rate",
    "detect_speech",
    "is_speaking",
]
