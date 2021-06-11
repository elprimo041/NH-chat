# -*- coding:utf-8 -*-
import subprocess
import wave
import time

print("Start recording...")
cmd = "sox -t waveaudio -d out.wav"
p = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)

# input("Enter to stop: ")
time.sleep(3)
p.terminate()
try:
    print("wait")
    p.wait(timeout=1)
except subprocess.TimeoutExpired:
    print("kill")
    p.kill()