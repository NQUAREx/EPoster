import queue
import sounddevice as sd
import vosk
import sys
import json

MODEL_PATH = "/home/nq/EPoster/voice/vosk-model-small-ru-0.22"
SAMPLE_RATE = 48000  # важно

device_index = 1  # заменить на свой

q = queue.Queue()

def callback(indata, frames, time, status):
    if status:
        print(status, file=sys.stderr)
    q.put(bytes(indata))

model = vosk.Model(MODEL_PATH)
rec = vosk.KaldiRecognizer(model, SAMPLE_RATE)

with sd.RawInputStream(
        samplerate=SAMPLE_RATE,
        blocksize=8000,
        device=device_index,
        dtype='int16',
        channels=1,
        callback=callback):

    print("Говорите...")
    while True:
        data = q.get()
        if rec.AcceptWaveform(data):
            result = json.loads(rec.Result())
            print("Распознано:", result.get("text"))
        else:
            partial = json.loads(rec.PartialResult())
            print("...", partial.get("partial"))