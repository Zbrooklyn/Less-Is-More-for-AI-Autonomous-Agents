"""Text-to-speech — synthesize and play speech via pyttsx3 (Windows SAPI / espeak)."""

from threading import Thread
from typing import Optional

try:
    import pyttsx3

    _HAS_PYTTSX3 = True
except ImportError:
    pyttsx3 = None  # type: ignore[assignment]
    _HAS_PYTTSX3 = False


# Module-level engine singleton (lazy-init).
_engine: Optional[object] = None


def _get_engine():
    """Return (or create) the pyttsx3 engine singleton."""
    global _engine
    if not _HAS_PYTTSX3:
        raise ImportError(
            "pyttsx3 is required for text-to-speech. "
            "Install it: pip install pyttsx3"
        )
    if _engine is None:
        _engine = pyttsx3.init()
    return _engine


def speak(text: str) -> None:
    """Synthesize *text* and play it through the default audio output (blocking)."""
    engine = _get_engine()
    engine.say(text)  # type: ignore[union-attr]
    engine.runAndWait()  # type: ignore[union-attr]


def speak_async(text: str) -> Thread:
    """Non-blocking version of :func:`speak`. Returns the background thread."""
    t = Thread(target=speak, args=(text,), daemon=True)
    t.start()
    return t


def save_speech(text: str, path: str) -> None:
    """Render *text* to an audio file at *path* (WAV or MP3 depending on engine)."""
    engine = _get_engine()
    engine.save_to_file(text, path)  # type: ignore[union-attr]
    engine.runAndWait()  # type: ignore[union-attr]


def list_voices() -> list[dict]:
    """Return available TTS voices with id, name, and language."""
    engine = _get_engine()
    voices = engine.getProperty("voices")  # type: ignore[union-attr]
    result = []
    for v in voices:
        result.append(
            {
                "id": v.id,
                "name": v.name,
                "languages": getattr(v, "languages", []),
            }
        )
    return result


def set_voice(voice_id: str) -> None:
    """Set the TTS voice by its identifier string."""
    engine = _get_engine()
    engine.setProperty("voice", voice_id)  # type: ignore[union-attr]


def set_rate(rate: int) -> None:
    """Set the speech rate in words per minute (default ~200)."""
    engine = _get_engine()
    engine.setProperty("rate", rate)  # type: ignore[union-attr]
