"""Microphone capture — records audio from the default input device."""

import io
import wave
from threading import Thread, Event
from typing import Optional

import numpy as np

try:
    import sounddevice as sd

    _HAS_SOUNDDEVICE = True
except ImportError:
    sd = None  # type: ignore[assignment]
    _HAS_SOUNDDEVICE = False


def _require_sounddevice():
    if not _HAS_SOUNDDEVICE:
        raise ImportError(
            "sounddevice is required for audio capture. "
            "Install it: pip install sounddevice"
        )


class AudioCapture:
    """Record audio from the system microphone.

    Parameters
    ----------
    sample_rate : int
        Sample rate in Hz.  Whisper expects 16 000.
    channels : int
        Number of audio channels (1 = mono).
    """

    def __init__(self, sample_rate: int = 16000, channels: int = 1):
        _require_sounddevice()
        self.sample_rate = sample_rate
        self.channels = channels
        self._frames: list[np.ndarray] = []
        self._recording = False
        self._stop_event = Event()
        self._thread: Optional[Thread] = None

    # -- public API ----------------------------------------------------------

    @property
    def is_recording(self) -> bool:
        return self._recording

    def start(self) -> None:
        """Begin recording in a background thread."""
        if self._recording:
            return
        self._frames = []
        self._recording = True
        self._stop_event.clear()
        self._thread = Thread(target=self._record_loop, daemon=True)
        self._thread.start()

    def stop(self) -> np.ndarray:
        """Stop recording and return captured audio as a numpy array."""
        if not self._recording:
            return np.array([], dtype=np.float32)
        self._recording = False
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)
        self._thread = None
        if not self._frames:
            return np.array([], dtype=np.float32)
        return np.concatenate(self._frames, axis=0).flatten()

    def record(self, duration_seconds: float) -> np.ndarray:
        """Record for a fixed duration and return the audio as a numpy array."""
        _require_sounddevice()
        samples = int(duration_seconds * self.sample_rate)
        audio = sd.rec(
            samples,
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype="float32",
        )
        sd.wait()
        return audio.flatten()

    @staticmethod
    def save_wav(audio_data: np.ndarray, path: str, sample_rate: int = 16000) -> None:
        """Save a numpy audio array to a WAV file (16-bit PCM)."""
        audio_int16 = np.clip(audio_data * 32767, -32768, 32767).astype(np.int16)
        with wave.open(path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(sample_rate)
            wf.writeframes(audio_int16.tobytes())

    @staticmethod
    def list_devices() -> list[dict]:
        """Return a list of available audio input/output devices."""
        _require_sounddevice()
        devices = sd.query_devices()
        result = []
        if isinstance(devices, dict):
            devices = [devices]
        for d in devices:
            result.append(
                {
                    "name": d.get("name", ""),
                    "index": d.get("index", 0),
                    "max_input_channels": d.get("max_input_channels", 0),
                    "max_output_channels": d.get("max_output_channels", 0),
                    "default_samplerate": d.get("default_samplerate", 0),
                }
            )
        return result

    # -- internals -----------------------------------------------------------

    def _record_loop(self) -> None:
        """Background recording loop using sounddevice InputStream."""
        block_size = int(self.sample_rate * 0.1)  # 100 ms blocks

        def _callback(indata, frames, time_info, status):  # noqa: ARG001
            if self._recording:
                self._frames.append(indata.copy())

        try:
            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype="float32",
                blocksize=block_size,
                callback=_callback,
            ):
                self._stop_event.wait()
        except Exception:
            self._recording = False
