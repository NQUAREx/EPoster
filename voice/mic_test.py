from __future__ import annotations

import argparse
import json
import queue
import time
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Minimal microphone STT test")
    parser.add_argument("--model-path", required=True)
    parser.add_argument("--device", default="plughw:2,0")
    parser.add_argument("--samplerate", type=int, default=4000)
    parser.add_argument("--seconds", type=float, default=4.0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    import sounddevice as sd
    from vosk import KaldiRecognizer, Model

    model_dir = Path(args.model_path).expanduser().resolve()
    model = Model(str(model_dir))
    recognizer = KaldiRecognizer(model, args.samplerate)
    audio_queue: queue.Queue[bytes] = queue.Queue(maxsize=40)

    def callback(indata, frames, time_info, status):  # noqa: ANN001
        if status:
            return
        try:
            audio_queue.put_nowait(bytes(indata))
        except queue.Full:
            pass

    print(f"[mic-test] device={args.device}, samplerate={args.samplerate}")
    with sd.RawInputStream(
        device=args.device,
        samplerate=args.samplerate,
        blocksize=0,
        dtype="int16",
        channels=1,
        callback=callback,
    ):
        started = time.monotonic()
        while time.monotonic() - started < args.seconds:
            try:
                data = audio_queue.get(timeout=0.2)
            except queue.Empty:
                continue
            if recognizer.AcceptWaveform(data):
                result = json.loads(recognizer.Result())
                text = str(result.get("text", "")).strip()
                if text:
                    print(f"[mic-test] recognized: {text}")

    final_result = json.loads(recognizer.FinalResult())
    final_text = str(final_result.get("text", "")).strip()
    print(f"[mic-test] final: {final_text}")


if __name__ == "__main__":
    main()
