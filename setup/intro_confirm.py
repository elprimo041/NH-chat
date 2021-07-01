# -*- coding:utf-8 -*-
print("NH-chatの導入状況を確認します")
# RLをパスに追加
import os
import sys
sys.path.append(os.path.join(os.getcwd(), '../src/Interface'))
sys.path.append(os.path.join(os.getcwd(), '../src/RL'))

from nh_path import NHPath


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

    from google.cloud import speech
    import pyaudio
    from six.moves import queue
    import MeCab

    print("モジュールは正しくインストールされています")
    print("==========================================")

except ModuleNotFoundError as e:
    print(e)
    import sys
    sys.exit()

print("自作モジュールの読み込みテストを行います")
try:
    from abstract_chat import AbstractChat
    from abstract_communicator import AbstractCommunicator
    from google_asr import ResumableMicrophoneStream, GoogleASR
    from julius_asr import JuliusASR
    from manage_task import ManageTask
    from manage_turn import ManageTrun
    from nh_chat import NHChat
    from nh_path import NHPath
    from tcp_client import TCPClient
    from tools import Record, OpenSmile, OpenFace, MMDAgent
    print("自作モジュールは正しくインストールされています")
    print("==========================================")
    
except ModuleNotFoundError as e:
    print(e)
    import sys
    sys.exit()

def PlayWavFie(Filename):
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
result_path = "data/result"
if os.path.isdir(result_path):
    shutil.rmtree(result_path)
    time.sleep(0.2)
os.mkdir(result_path)
nh_path = NHPath()

print("MeCabの動作確認を行います")
m = MeCab.Tagger ("-Ochasen")
print("想定される出力")
print("すもも  スモモ  すもも  名詞-一般\n\
も      モ      も      助詞-係助詞\n\
もも    モモ    もも    名詞-一般\n\
も      モ      も      助詞-係助詞\n\
もも    モモ    もも    名詞-一般\n\
の      ノ      の      助詞-連体化\n\
うち    ウチ    うち    名詞-非自立-副詞可能\n\
EOS")
print("ーーーーーーーーーーーーーーーーーーーーーーーーーーー")
print("実際の出力")
print(m.parse ("すもももももももものうち"))
is_correct_MeCab = input("想定される出力と実際の出力は同じでしたか？\ny/n>>")
if is_correct_MeCab == "y":
    print("MeCabの動作を確認しました")
    print("==========================================")
else:
    print("インストール時の文字コード，MeCabへのパスなどを確認してください")
    sys.exit()

print("openfaceの動作確認を行います")
face_result_path = "data/result/sample_face.csv"
openface = OpenFace()
openface.start(face_result_path)
print("3秒間トラッキングを行います")
time.sleep(3)
openface.stop()
if os.path.isfile(face_result_path):
    print("openfaceの動作を確認しました")
    print("==========================================")
else:
    raise Exception("openfaceが正しく動作していません")
    sys.exit()

print("録音機能の動作確認を行います")
rec = Record()

wav_path = "data/result/sample_sound.wav"
print("5秒間の録音を行います．何か話してみてください．")
for i in range(3):
    print("\r録音開始まで"+str(3-i), end="")
    time.sleep(1)
print("\n録音中...")
rec.start(wav_path)
time.sleep(5)
rec.stop()
if os.path.isfile(wav_path):
    pass
else:
    raise Exception("録音機能が正しく動作していません")
    sys.exit()
print("録音した音声を再生します")
PlayWavFie(wav_path)
is_correct_play = input("録音した音声が再生されましたか？\ny/n>>")
if is_correct_play == "y":
    print("録音機能の動作を確認しました")
    print("==========================================")
else:
    print("入力デバイスを確認してください")
    sys.exit()

print("opensmileの動作確認を行います")
opensmile = OpenSmile()
opensmile.run(wav_path)
if (os.path.isfile("{}.arff".format(wav_path[:-4]))) and\
   (os.path.isfile("{}.csv".format(wav_path[:-4]))):
    print("opensmileの動作を確認しました")
    print("==========================================")
else:
    raise Exception("opensmileが正しく動作していません")
    sys.exit()

print("MMDAgentの動作確認を行います")
mmd = MMDAgent()
mmd.say("MMDAgentの動作確認です")
mmd.move("mei_bye")
mmd.say("さようなら")
time.sleep(2)
mmd.end()
print("MMDAgentの動作を確認しました")
print("==========================================")

print("Google音声認識の動作確認を行います")
google = GoogleASR(response_time_no_word=6.0, turn_buffer=1.5)
for i in range(2):
    print("turn {}".format(i+1))
    google.start()
    while not google.m_turn.is_sys_turn_end:
        time.sleep(0.1)
    print("GoogleASR result:{}".format(google.read_result()))
print("Google音声認識の動作を確認しました")
print("==========================================")
    
is_julius = input("Julius音声認識の動作確認を行いますか？\ny/n>>")
if is_julius == "y":
    print("Julius音声認識の動作確認を行います")
    p = NHPath()
    julius_path = p.path["julius"]
    if os.path.exists(julius_path) == False:
        print("dictation kitのフォルダが存在しません")
        sys.exit()
    julius = JuliusASR(response_time_no_word=6.0, turn_buffer=1.5)
    for i in range(2):
        print("turn {}".format(i+1))
        julius.start()
        while not julius.m_turn.is_sys_turn_end:
            time.sleep(0.1)
        print("JuliusASR result:{}".format(julius.read_result()))
    print("Julius音声認識の動作を確認しました")
    print("==========================================")
    
    

print("正しく環境構築されていることを確認しました")
print("プログラムを終了します")


