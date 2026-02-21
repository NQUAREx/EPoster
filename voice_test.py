import json
import queue
import sys

import sounddevice as sd
import vosk

MODEL_PATH = "/home/nq/EPoster/voice/vosk-model-small-ru-0.22"
SAMPLE_RATE = 48000
DEVICE_INDEX = 1


def callback(indata, frames, time, status):
    del frames, time
    if status:
        print(status, file=sys.stderr)
    AUDIO_QUEUE.put(bytes(indata))


def run_voice_test(model_path: str = MODEL_PATH, sample_rate: int = SAMPLE_RATE, device_index: int = DEVICE_INDEX) -> None:
    model = vosk.Model(model_path)
    recognizer = vosk.KaldiRecognizer(model, sample_rate)

    with sd.RawInputStream(
        samplerate=sample_rate,
        blocksize=8000,
        device=device_index,
        dtype="int16",
        channels=1,
        callback=callback,
    ):
        print("Говорите...")
        while True:
            data = AUDIO_QUEUE.get()
            if recognizer.AcceptWaveform(data):
                result = json.loads(recognizer.Result())
                print("Распознано:", result.get("text"))
            else:
                partial = json.loads(recognizer.PartialResult())
                print("...", partial.get("partial"))


AUDIO_QUEUE = queue.Queue()

if __name__ == "__main__":
    run_voice_test()
