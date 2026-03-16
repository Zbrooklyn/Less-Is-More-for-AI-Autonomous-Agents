"""Speech-to-text — transcribe audio using OpenAI Whisper (or a stub if unavailable)."""

from dataclasses import dataclass, field
from typing import Optional

import numpy as np

try:
    import whisper as _whisper

    _HAS_WHISPER = True
except ImportError:
    _whisper = None  # type: ignore[assignment]
    _HAS_WHISPER = False


@dataclass
class TranscriptionResult:
    """Result of a speech-to-text transcription."""

    text: str = ""
    segments: list[dict] = field(default_factory=list)
    language: str = ""
    duration: float = 0.0


# Cache loaded models to avoid reloading on every call.
_model_cache: dict[str, object] = {}


def _get_model(model: str = "base"):
    """Load (or return cached) Whisper model."""
    if not _HAS_WHISPER:
        raise ImportError(
            "Whisper is required for transcription. "
            "Install it: pip install openai-whisper  "
            "(Note: this pulls PyTorch and is ~2 GB.)"
        )
    if model not in _model_cache:
        _model_cache[model] = _whisper.load_model(model)
    return _model_cache[model]


def transcribe(
    audio_data: np.ndarray,
    model: str = "base",
    language: Optional[str] = None,
) -> TranscriptionResult:
    """Transcribe a numpy audio array (float32, 16 kHz mono).

    Parameters
    ----------
    audio_data : np.ndarray
        Audio samples as float32 in [-1, 1].
    model : str
        Whisper model size (tiny, base, small, medium, large).
    language : str, optional
        Force a specific language for decoding.

    Returns
    -------
    TranscriptionResult
    """
    mdl = _get_model(model)

    # Whisper expects float32 1-D array.
    audio_data = audio_data.astype(np.float32).flatten()
    duration = len(audio_data) / 16000.0

    decode_options = {}
    if language:
        decode_options["language"] = language

    result = mdl.transcribe(audio_data, **decode_options)  # type: ignore[union-attr]

    segments = [
        {
            "start": seg["start"],
            "end": seg["end"],
            "text": seg["text"],
        }
        for seg in result.get("segments", [])
    ]

    return TranscriptionResult(
        text=result.get("text", "").strip(),
        segments=segments,
        language=result.get("language", ""),
        duration=duration,
    )


def transcribe_file(
    path: str,
    model: str = "base",
    language: Optional[str] = None,
) -> TranscriptionResult:
    """Transcribe audio from a WAV file on disk.

    Parameters
    ----------
    path : str
        Path to a WAV file (16 kHz mono recommended).
    model : str
        Whisper model size.
    language : str, optional
        Force a specific language.

    Returns
    -------
    TranscriptionResult
    """
    import wave

    with wave.open(path, "rb") as wf:
        sample_rate = wf.getframerate()
        n_frames = wf.getnframes()
        raw = wf.readframes(n_frames)

    # Convert 16-bit PCM to float32 in [-1, 1].
    audio = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0

    # Resample to 16 kHz if needed (simple linear interpolation).
    if sample_rate != 16000:
        target_len = int(len(audio) * 16000 / sample_rate)
        audio = np.interp(
            np.linspace(0, len(audio), target_len, endpoint=False),
            np.arange(len(audio)),
            audio,
        )

    return transcribe(audio, model=model, language=language)
