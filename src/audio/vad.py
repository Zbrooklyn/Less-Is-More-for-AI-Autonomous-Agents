"""Voice Activity Detection — simple energy-based VAD (no ML dependency)."""

import numpy as np


def _rms(chunk: np.ndarray) -> float:
    """Root-mean-square energy of an audio chunk."""
    if len(chunk) == 0:
        return 0.0
    return float(np.sqrt(np.mean(chunk.astype(np.float64) ** 2)))


def is_speaking(audio_chunk: np.ndarray, threshold: float = 0.02) -> bool:
    """Return True if the RMS energy of *audio_chunk* exceeds *threshold*.

    Parameters
    ----------
    audio_chunk : np.ndarray
        Short audio segment (float32, typically 10-100 ms).
    threshold : float
        Energy threshold; values above indicate speech.
    """
    return _rms(audio_chunk) > threshold


def detect_speech(
    audio_data: np.ndarray,
    threshold: float = 0.02,
    min_duration: float = 0.3,
    sample_rate: int = 16000,
    frame_ms: int = 30,
) -> list[dict]:
    """Detect speech segments in *audio_data* using RMS energy thresholding.

    Parameters
    ----------
    audio_data : np.ndarray
        Audio samples (float32, mono).
    threshold : float
        RMS energy threshold for speech.
    min_duration : float
        Minimum segment duration in seconds to keep.
    sample_rate : int
        Sample rate of the audio.
    frame_ms : int
        Analysis frame size in milliseconds.

    Returns
    -------
    list[dict]
        Each dict has ``start`` and ``end`` keys (float, seconds).
    """
    audio_data = audio_data.astype(np.float32).flatten()
    frame_size = int(sample_rate * frame_ms / 1000)

    if frame_size == 0 or len(audio_data) == 0:
        return []

    n_frames = len(audio_data) // frame_size
    if n_frames == 0:
        return []

    # Classify each frame as speech or silence.
    speech_flags = []
    for i in range(n_frames):
        chunk = audio_data[i * frame_size : (i + 1) * frame_size]
        speech_flags.append(_rms(chunk) > threshold)

    # Merge contiguous speech frames into segments.
    segments: list[dict] = []
    seg_start: int | None = None
    for i, is_speech in enumerate(speech_flags):
        if is_speech and seg_start is None:
            seg_start = i
        elif not is_speech and seg_start is not None:
            segments.append({"start": seg_start, "end": i})
            seg_start = None
    if seg_start is not None:
        segments.append({"start": seg_start, "end": n_frames})

    # Convert frame indices to seconds and filter by min_duration.
    frame_sec = frame_ms / 1000.0
    result = []
    for seg in segments:
        start_sec = seg["start"] * frame_sec
        end_sec = seg["end"] * frame_sec
        if (end_sec - start_sec) >= min_duration:
            result.append({"start": round(start_sec, 4), "end": round(end_sec, 4)})

    return result
