"""Tests for audio I/O — capture, transcription, TTS, and VAD.

ALL external audio hardware and heavy dependencies are mocked.
"""

import os
import tempfile
import wave
from unittest.mock import MagicMock, patch, PropertyMock

import numpy as np
import pytest


# ============================================================
# AudioCapture
# ============================================================

class TestAudioCapture:
    def test_init_sets_sample_rate(self):
        with patch("src.audio.capture._HAS_SOUNDDEVICE", True), \
             patch("src.audio.capture.sd", MagicMock()):
            from src.audio.capture import AudioCapture
            cap = AudioCapture(sample_rate=44100, channels=2)
            assert cap.sample_rate == 44100
            assert cap.channels == 2

    def test_init_default_values(self):
        with patch("src.audio.capture._HAS_SOUNDDEVICE", True), \
             patch("src.audio.capture.sd", MagicMock()):
            from src.audio.capture import AudioCapture
            cap = AudioCapture()
            assert cap.sample_rate == 16000
            assert cap.channels == 1

    def test_record_returns_numpy_array(self):
        fake_audio = np.zeros((16000,), dtype=np.float32)
        mock_sd = MagicMock()
        mock_sd.rec.return_value = fake_audio.reshape(-1, 1)
        mock_sd.wait.return_value = None

        with patch("src.audio.capture._HAS_SOUNDDEVICE", True), \
             patch("src.audio.capture.sd", mock_sd):
            from src.audio.capture import AudioCapture
            cap = AudioCapture()
            result = cap.record(1.0)

        assert isinstance(result, np.ndarray)
        assert len(result) == 16000
        mock_sd.rec.assert_called_once()
        mock_sd.wait.assert_called_once()

    def test_save_wav_creates_file(self):
        audio = np.random.uniform(-0.5, 0.5, 16000).astype(np.float32)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            path = f.name

        try:
            # save_wav is a static method — no sounddevice needed.
            from src.audio.capture import AudioCapture
            AudioCapture.save_wav(audio, path, sample_rate=16000)

            assert os.path.exists(path)
            assert os.path.getsize(path) > 0

            # Verify it's a valid WAV.
            with wave.open(path, "rb") as wf:
                assert wf.getnchannels() == 1
                assert wf.getframerate() == 16000
                assert wf.getsampwidth() == 2
                assert wf.getnframes() == 16000
        finally:
            os.unlink(path)

    def test_list_devices_returns_list(self):
        mock_sd = MagicMock()
        mock_sd.query_devices.return_value = [
            {
                "name": "Microphone",
                "index": 0,
                "max_input_channels": 2,
                "max_output_channels": 0,
                "default_samplerate": 44100.0,
            },
            {
                "name": "Speakers",
                "index": 1,
                "max_input_channels": 0,
                "max_output_channels": 2,
                "default_samplerate": 48000.0,
            },
        ]

        with patch("src.audio.capture._HAS_SOUNDDEVICE", True), \
             patch("src.audio.capture.sd", mock_sd):
            from src.audio.capture import AudioCapture
            devices = AudioCapture.list_devices()

        assert isinstance(devices, list)
        assert len(devices) == 2
        assert devices[0]["name"] == "Microphone"
        assert devices[1]["max_output_channels"] == 2

    def test_is_recording_property(self):
        with patch("src.audio.capture._HAS_SOUNDDEVICE", True), \
             patch("src.audio.capture.sd", MagicMock()):
            from src.audio.capture import AudioCapture
            cap = AudioCapture()
            assert cap.is_recording is False

    def test_stop_without_start_returns_empty(self):
        with patch("src.audio.capture._HAS_SOUNDDEVICE", True), \
             patch("src.audio.capture.sd", MagicMock()):
            from src.audio.capture import AudioCapture
            cap = AudioCapture()
            result = cap.stop()
            assert isinstance(result, np.ndarray)
            assert len(result) == 0

    def test_missing_sounddevice_raises(self):
        with patch("src.audio.capture._HAS_SOUNDDEVICE", False):
            from src.audio.capture import AudioCapture
            with pytest.raises(ImportError, match="sounddevice"):
                AudioCapture()


# ============================================================
# Transcribe
# ============================================================

class TestTranscribe:
    def test_transcribe_returns_result(self):
        mock_model = MagicMock()
        mock_model.transcribe.return_value = {
            "text": "Hello world",
            "segments": [{"start": 0.0, "end": 1.0, "text": "Hello world"}],
            "language": "en",
        }

        mock_whisper = MagicMock()
        mock_whisper.load_model.return_value = mock_model

        with patch.dict("sys.modules", {"whisper": mock_whisper}), \
             patch("src.audio.transcribe._HAS_WHISPER", True), \
             patch("src.audio.transcribe._whisper", mock_whisper), \
             patch("src.audio.transcribe._model_cache", {}):
            from src.audio.transcribe import transcribe, TranscriptionResult
            audio = np.zeros(16000, dtype=np.float32)
            result = transcribe(audio, model="base")

        assert isinstance(result, TranscriptionResult)
        assert result.text == "Hello world"
        assert result.language == "en"
        assert len(result.segments) == 1
        assert result.duration == pytest.approx(1.0, abs=0.01)

    def test_transcribe_file_reads_wav(self):
        # Create a temporary WAV file.
        audio_int16 = np.zeros(16000, dtype=np.int16)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            path = f.name
        with wave.open(path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            wf.writeframes(audio_int16.tobytes())

        mock_model = MagicMock()
        mock_model.transcribe.return_value = {
            "text": "test",
            "segments": [],
            "language": "en",
        }
        mock_whisper = MagicMock()
        mock_whisper.load_model.return_value = mock_model

        try:
            with patch.dict("sys.modules", {"whisper": mock_whisper}), \
                 patch("src.audio.transcribe._HAS_WHISPER", True), \
                 patch("src.audio.transcribe._whisper", mock_whisper), \
                 patch("src.audio.transcribe._model_cache", {}):
                from src.audio.transcribe import transcribe_file
                result = transcribe_file(path)

            assert result.text == "test"
            mock_model.transcribe.assert_called_once()
        finally:
            os.unlink(path)

    def test_transcribe_missing_whisper_raises(self):
        with patch("src.audio.transcribe._HAS_WHISPER", False):
            from src.audio.transcribe import transcribe
            with pytest.raises(ImportError, match="Whisper"):
                transcribe(np.zeros(100, dtype=np.float32))

    def test_transcription_result_defaults(self):
        from src.audio.transcribe import TranscriptionResult
        r = TranscriptionResult()
        assert r.text == ""
        assert r.segments == []
        assert r.language == ""
        assert r.duration == 0.0


# ============================================================
# TTS
# ============================================================

class TestTTS:
    def test_speak_calls_engine(self):
        mock_engine = MagicMock()
        mock_pyttsx3 = MagicMock()
        mock_pyttsx3.init.return_value = mock_engine

        with patch("src.audio.tts._HAS_PYTTSX3", True), \
             patch("src.audio.tts.pyttsx3", mock_pyttsx3), \
             patch("src.audio.tts._engine", None):
            from src.audio.tts import speak
            speak("Hello")

        mock_engine.say.assert_called_once_with("Hello")
        mock_engine.runAndWait.assert_called_once()

    def test_speak_async_is_non_blocking(self):
        mock_engine = MagicMock()
        mock_pyttsx3 = MagicMock()
        mock_pyttsx3.init.return_value = mock_engine

        with patch("src.audio.tts._HAS_PYTTSX3", True), \
             patch("src.audio.tts.pyttsx3", mock_pyttsx3), \
             patch("src.audio.tts._engine", None):
            from src.audio.tts import speak_async
            thread = speak_async("Hello async")
            thread.join(timeout=5.0)

        # Engine should have been called from the thread.
        mock_engine.say.assert_called_once_with("Hello async")
        assert not thread.is_alive()

    def test_save_speech(self):
        mock_engine = MagicMock()
        mock_pyttsx3 = MagicMock()
        mock_pyttsx3.init.return_value = mock_engine

        with patch("src.audio.tts._HAS_PYTTSX3", True), \
             patch("src.audio.tts.pyttsx3", mock_pyttsx3), \
             patch("src.audio.tts._engine", None):
            from src.audio.tts import save_speech
            save_speech("Save this", "output.wav")

        mock_engine.save_to_file.assert_called_once_with("Save this", "output.wav")
        mock_engine.runAndWait.assert_called_once()

    def test_list_voices(self):
        mock_voice = MagicMock()
        mock_voice.id = "voice1"
        mock_voice.name = "Microsoft David"
        mock_voice.languages = ["en_US"]

        mock_engine = MagicMock()
        mock_engine.getProperty.return_value = [mock_voice]

        mock_pyttsx3 = MagicMock()
        mock_pyttsx3.init.return_value = mock_engine

        with patch("src.audio.tts._HAS_PYTTSX3", True), \
             patch("src.audio.tts.pyttsx3", mock_pyttsx3), \
             patch("src.audio.tts._engine", None):
            from src.audio.tts import list_voices
            voices = list_voices()

        assert len(voices) == 1
        assert voices[0]["id"] == "voice1"
        assert voices[0]["name"] == "Microsoft David"

    def test_set_voice(self):
        mock_engine = MagicMock()
        mock_pyttsx3 = MagicMock()
        mock_pyttsx3.init.return_value = mock_engine

        with patch("src.audio.tts._HAS_PYTTSX3", True), \
             patch("src.audio.tts.pyttsx3", mock_pyttsx3), \
             patch("src.audio.tts._engine", None):
            from src.audio.tts import set_voice
            set_voice("voice1")

        mock_engine.setProperty.assert_called_with("voice", "voice1")

    def test_set_rate(self):
        mock_engine = MagicMock()
        mock_pyttsx3 = MagicMock()
        mock_pyttsx3.init.return_value = mock_engine

        with patch("src.audio.tts._HAS_PYTTSX3", True), \
             patch("src.audio.tts.pyttsx3", mock_pyttsx3), \
             patch("src.audio.tts._engine", None):
            from src.audio.tts import set_rate
            set_rate(150)

        mock_engine.setProperty.assert_called_with("rate", 150)

    def test_missing_pyttsx3_raises(self):
        with patch("src.audio.tts._HAS_PYTTSX3", False), \
             patch("src.audio.tts._engine", None):
            from src.audio.tts import speak
            with pytest.raises(ImportError, match="pyttsx3"):
                speak("hello")


# ============================================================
# VAD
# ============================================================

class TestVAD:
    def test_detect_speech_finds_segments(self):
        from src.audio.vad import detect_speech

        # Build audio: 0.5s silence, 0.5s loud, 0.5s silence.
        sr = 16000
        silence = np.zeros(int(sr * 0.5), dtype=np.float32)
        speech = np.random.uniform(-0.5, 0.5, int(sr * 0.5)).astype(np.float32)
        audio = np.concatenate([silence, speech, silence])

        segments = detect_speech(audio, threshold=0.02, min_duration=0.3, sample_rate=sr)
        assert len(segments) >= 1
        # Speech starts around 0.5s.
        assert segments[0]["start"] >= 0.4
        assert segments[0]["end"] <= 1.1

    def test_detect_speech_empty_audio(self):
        from src.audio.vad import detect_speech

        segments = detect_speech(np.array([], dtype=np.float32))
        assert segments == []

    def test_detect_speech_all_silence(self):
        from src.audio.vad import detect_speech

        audio = np.zeros(16000, dtype=np.float32)
        segments = detect_speech(audio, threshold=0.02, min_duration=0.3)
        assert segments == []

    def test_detect_speech_filters_short_segments(self):
        from src.audio.vad import detect_speech

        # Very short burst — should be filtered out by min_duration.
        sr = 16000
        silence = np.zeros(sr, dtype=np.float32)
        burst = np.ones(int(sr * 0.05), dtype=np.float32) * 0.5  # 50 ms
        audio = np.concatenate([silence, burst, silence])

        segments = detect_speech(audio, threshold=0.02, min_duration=0.3)
        assert segments == []

    def test_is_speaking_loud(self):
        from src.audio.vad import is_speaking

        loud = np.ones(480, dtype=np.float32) * 0.5
        assert is_speaking(loud, threshold=0.02) is True

    def test_is_speaking_silent(self):
        from src.audio.vad import is_speaking

        silent = np.zeros(480, dtype=np.float32)
        assert is_speaking(silent, threshold=0.02) is False


# ============================================================
# CLI
# ============================================================

class TestCLI:
    def test_cli_no_command_prints_help(self, capsys):
        from src.audio.cli import main
        ret = main([])
        assert ret == 1

    def test_cli_record_command(self):
        mock_cap_cls = MagicMock()
        mock_cap = MagicMock()
        mock_cap.record.return_value = np.zeros(16000, dtype=np.float32)
        mock_cap_cls.return_value = mock_cap

        with patch("src.audio.cli.sys") as mock_sys, \
             patch("src.audio.capture._HAS_SOUNDDEVICE", True), \
             patch("src.audio.capture.sd", MagicMock()):
            # Directly test the cmd_record function.
            from src.audio.cli import main
            with patch("src.audio.capture.AudioCapture", mock_cap_cls):
                # We need to also patch at the import site inside cmd_record.
                with patch("src.audio.capture.AudioCapture", mock_cap_cls):
                    from src.audio import capture
                    orig = capture.AudioCapture
                    capture.AudioCapture = mock_cap_cls
                    try:
                        ret = main(["record", "2", "--output", "test.wav"])
                    finally:
                        capture.AudioCapture = orig

        mock_cap.record.assert_called_once_with(2.0)

    def test_cli_transcribe_command(self):
        from src.audio.transcribe import TranscriptionResult

        mock_result = TranscriptionResult(
            text="hello", segments=[], language="en", duration=1.0
        )
        mock_transcribe_file = MagicMock(return_value=mock_result)

        with patch("src.audio.transcribe.transcribe_file", mock_transcribe_file):
            from src.audio.cli import main
            ret = main(["transcribe", "test.wav"])

        mock_transcribe_file.assert_called_once()

    def test_cli_speak_command(self):
        mock_speak = MagicMock()

        with patch("src.audio.cli.sys"):
            import src.audio.tts as tts_mod
            orig = tts_mod.speak
            tts_mod.speak = mock_speak
            try:
                from src.audio.cli import main
                ret = main(["speak", "hello", "world"])
            finally:
                tts_mod.speak = orig

        mock_speak.assert_called_once_with("hello world")

    def test_cli_devices_command(self):
        mock_list = MagicMock(return_value=[
            {"name": "Mic", "index": 0, "max_input_channels": 1,
             "max_output_channels": 0, "default_samplerate": 16000},
        ])

        with patch("src.audio.cli.sys"):
            import src.audio.capture as c_mod
            orig = c_mod.AudioCapture.list_devices
            c_mod.AudioCapture.list_devices = mock_list
            try:
                from src.audio.cli import main
                ret = main(["devices"])
            finally:
                c_mod.AudioCapture.list_devices = orig

        mock_list.assert_called_once()

    def test_cli_voices_command(self):
        mock_voices = MagicMock(return_value=[
            {"id": "v1", "name": "David", "languages": ["en"]},
        ])

        with patch("src.audio.cli.sys"):
            import src.audio.tts as tts_mod
            orig = tts_mod.list_voices
            tts_mod.list_voices = mock_voices
            try:
                from src.audio.cli import main
                ret = main(["voices"])
            finally:
                tts_mod.list_voices = orig

        mock_voices.assert_called_once()
