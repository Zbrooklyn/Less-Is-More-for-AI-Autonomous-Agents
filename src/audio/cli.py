"""audio-cli — Command-line interface for audio capture, transcription, and TTS."""

import argparse
import sys


def cmd_record(args) -> int:
    """Record audio from the microphone."""
    from src.audio.capture import AudioCapture

    try:
        cap = AudioCapture(sample_rate=16000, channels=1)
        print(f"Recording for {args.seconds} seconds...")
        audio = cap.record(args.seconds)
        output = args.output or "recording.wav"
        cap.save_wav(audio, output)
        print(f"Saved {len(audio)} samples to {output}")
        return 0
    except ImportError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_transcribe(args) -> int:
    """Transcribe a WAV file."""
    from src.audio.transcribe import transcribe_file

    try:
        result = transcribe_file(args.path, model=args.model)
        print(f"Language: {result.language}")
        print(f"Duration: {result.duration:.1f}s")
        print(f"Text: {result.text}")
        if args.segments:
            for seg in result.segments:
                print(f"  [{seg['start']:.1f}s - {seg['end']:.1f}s] {seg['text']}")
        return 0
    except ImportError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_speak(args) -> int:
    """Speak text aloud."""
    from src.audio.tts import speak as tts_speak

    try:
        text = " ".join(args.text)
        tts_speak(text)
        return 0
    except ImportError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_devices(_args) -> int:
    """List audio devices."""
    from src.audio.capture import AudioCapture

    try:
        devices = AudioCapture.list_devices()
        if not devices:
            print("No audio devices found.")
            return 0
        print(f"{'#':<4} {'Name':<40} {'In':<4} {'Out':<4} {'Rate'}")
        print("-" * 65)
        for d in devices:
            print(
                f"{d['index']:<4} {d['name']:<40} "
                f"{d['max_input_channels']:<4} {d['max_output_channels']:<4} "
                f"{d['default_samplerate']}"
            )
        return 0
    except ImportError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_voices(_args) -> int:
    """List available TTS voices."""
    from src.audio.tts import list_voices

    try:
        voices = list_voices()
        if not voices:
            print("No voices found.")
            return 0
        for v in voices:
            print(f"  {v['id']}")
            print(f"    Name: {v['name']}")
        return 0
    except ImportError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def main(argv=None) -> int:
    """CLI entry point for audio subsystem."""
    parser = argparse.ArgumentParser(
        prog="audio", description="Audio capture, transcription, and TTS"
    )
    sub = parser.add_subparsers(dest="command")

    # record
    p_record = sub.add_parser("record", help="Record audio from microphone")
    p_record.add_argument("seconds", type=float, help="Duration in seconds")
    p_record.add_argument("--output", "-o", help="Output WAV path")

    # transcribe
    p_trans = sub.add_parser("transcribe", help="Transcribe a WAV file")
    p_trans.add_argument("path", help="Path to WAV file")
    p_trans.add_argument("--model", default="base", help="Whisper model size")
    p_trans.add_argument("--segments", action="store_true", help="Show segments")

    # speak
    p_speak = sub.add_parser("speak", help="Speak text aloud")
    p_speak.add_argument("text", nargs="+", help="Text to speak")

    # devices
    sub.add_parser("devices", help="List audio devices")

    # voices
    sub.add_parser("voices", help="List TTS voices")

    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 1

    commands = {
        "record": cmd_record,
        "transcribe": cmd_transcribe,
        "speak": cmd_speak,
        "devices": cmd_devices,
        "voices": cmd_voices,
    }
    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main() or 0)
