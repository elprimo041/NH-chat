# -*- coding:utf-8 -*-
print("NH-chatの導入状況を確認します")

print("必要なモジュールがインストールされているか確認します")
print("==========================================")
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

except ModuleNotFoundError as e:
	print(e)

	print()
	import sys
	sys.exit()


print("==========================================")
print("必要なアプリがインストールされているか確認します")
import nh_chat
print("open faceの確認")
of = nh_chat.OpenFace()