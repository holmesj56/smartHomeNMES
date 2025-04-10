# -*- coding: utf-8 -*-
"""
Created on Fri Mar 28 20:25:06 2025

@author: moral
"""

import os
import queue
import sounddevice as sd
import vosk
import sys
import json

model_path = r"C:\Users\moral\OneDrive\Documents\EGR_555_NMES\vosk-model-small-en-us-0.15"

# Load the model
if not os.path.exists(model_path):
    print("Model not found. Check the path.")
    exit()

model = vosk.Model(model_path)

# Sampling rate
samplerate = 16000  
q = queue.Queue()

def callback(indata, frames, time, status):
    if status:
        print(status, file=sys.stderr)
    q.put(bytes(indata))

# Start audio stream
with sd.RawInputStream(samplerate=samplerate, blocksize=8000, dtype='int16',
                       channels=1, callback=callback):
    print("Speak into the mic (Ctrl+C to stop)...")
    rec = vosk.KaldiRecognizer(model, samplerate)

    while True:
        data = q.get()
        if rec.AcceptWaveform(data):
            result = json.loads(rec.Result())
            print("You said:", result.get("text", ""))
