# -*- coding:utf-8 -*-
print("NH-chatの導入状況を確認します")

print("必要なモジュールがインストールされているか確認します")
try:
	import socket
	import time
	import subprocess
	import pandas as pd
	import pickle
	import numpy as np
	import pyaudio
	import wave
	import time
	import threading
	import datetime
	import os
	import csv
	import shutil
	from PIL import ImageGrab
	import win32gui
	import win32con
	from screeninfo import get_monitors
	from optparse import OptionParser
	import warnings
	warnings.filterwarnings('ignore')
	import csv
	import time
	import subprocess
	import os
	import threading
	import re
	import sys
	from multiprocessing import Value
	import colorama
	colorama.init()
	import time
	import csv
	import socket
	import os
	import datetime
	import subprocess
	from socket import gethostname

	from google.cloud import speech_v1p1beta1 as speech
	import pyaudio
	from six.moves import queue

	from kill_task import kill_task
	print("モジュールは正しくインストールされています")
	print("==========================================")

except ModuleNotFoundError as e:
	print(e)

	print()
	import sys
	sys.exit()

def PlayWavFie(Filename = "sample.wav"):
	try:
		wf = wave.open(Filename, "r")
	except FileNotFoundError: #ファイルが存在しなかった場合
		print("[Error 404] No such file or directory: " + Filename)
		return 0
		
	# ストリームを開く
	p = pyaudio.PyAudio()
	stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
					channels=wf.getnchannels(),
					rate=wf.getframerate(),
					output=True)

	# 音声を再生
	chunk = 1024
	data = wf.readframes(chunk)
	while data != '':
		stream.write(data)
		data = wf.readframes(chunk)
		if data == b"":
			break
	stream.close()
	p.terminate()


print("必要なアプリの動作を確認します")
import nh_chat
result_path = "intro_confirm/result"
if os.path.isdir(result_path):
	shutil.rmtree(result_path)
	time.sleep(0.2)
os.mkdir(result_path)


print("openfaceの動作確認を行います")
openface_path = ""
with open("refData/path.csv") as f:
	reader = csv.reader(f)
	openface_path = ""
	for row in reader:
		if row[0] == "openface":
			openface_path = row[1]
			break
if openface_path == "":
	raise Exception("opensmile path undefined")
command = "{}/FaceLandmarkImg.exe -f intro_confirm/data/sample.jpg -out_dir intro_confirm/result/ > nul"\
	.format(openface_path)
subprocess.call(command, shell=True)

if os.path.isfile("intro_confirm/result/sample_of_details.txt"):
	print("openfaceの動作を確認しました")
else:
	raise Exception("openfaceが正しく動作していません")
	sys.exit()

rec = nh_chat.Record()
print("録音機能の動作確認を行います")
print("5秒間の録音を行います．何か話してみてください．")
for i in range(3):
    print("\r録音開始まで"+str(3-i), end="")
    time.sleep(1)
print("\n録音中")
rec.start("intro_confirm/data/sample.wav")
time.sleep(5)
rec.stop()
if os.path.isfile("intro_confirm/data/sample.wav"):
	pass
else:
	raise Exception("録音機能が正しく動作していません")
	sys.exit()
print("録音した音声を再生します")
PlayWavFie("intro_confirm/data/sample.wav")
is_correct_play = input("録音した音声が再生されましたか？\ny/n>>")
if is_correct_play == "y":
	print("録音機能の動作を確認しました")
else:
	print("入力デバイスを確認してください")
	sys.exit()


print("opensmileの動作確認を行います")
opensmile_path = ""
with open("refData/path.csv") as f:
	reader = csv.reader(f)
	for row in reader:
		if row[0] == "opensmile":
			opensmile_path = row[1]
			break
if opensmile_path == "":
	raise Exception("opensmile path undefined")
command = "{}/bin/SMILExtract.exe -C {}/config/is09-13/IS09_emotion.conf -I intro_confirm/data/sample.wav -O intro_confirm/result/sample.arff"\
	.format(opensmile_path, opensmile_path)
subprocess.call(command.split(" "), shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
if os.path.isfile("intro_confirm/result/sample.arff"):
	print("opensmileの動作を確認しました")
else:
	raise Exception("opensmileが正しく動作していません")
	sys.exit()

print("MMDAgentの動作確認を行います")
import mmd
mmd = mmd.MMDAgent()
mmd.say("MMDAgentの動作確認です")
mmd.move("mei_bye")
mmd.say("さようなら")
time.sleep(2)
mmd.end()

print("正しく環境構築されていることを確認しました")
print("プログラムを終了します")