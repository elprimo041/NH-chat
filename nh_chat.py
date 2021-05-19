# -*- coding:utf-8 -*-
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

from mmd import AbstractChat
import extFaceFea as eff
import extTextFea as etf
import predUI as pf
from theme import HistoryTheme
from dialogue_env import DialogueEnv
from agent import TrainedQlearningAgent


class NHChat(AbstractChat):


	def __init__(self, model="200117_c099", mode="WebCamera", user="tmp_user",\
		 turn_num=3, text=True, ASR_module="Google"):
		super().__init__(text=text, ASR_module=ASR_module)
		self.base_time = time.time()
		self.mode = mode
		self.env = DialogueEnv()
		self.record = Record()
		self.opensmile = OpenSmile()
		self.openface = OpenFace(user=user)
		Qtable_name = '{}/{}_Q'.format(model, model)
		self.log_name = '{}/{}_log.csv'.format(model, model) 
		self.agent = TrainedQlearningAgent(Qtable_name)
		self.agent.fillQ(self.env)
		self.state = self.env.reset()
		self.themeHis = HistoryTheme()
		self.current_turn = 0
		self.turn_num = turn_num
		self.user = user
		self.user_impression = None
		self.base_time = time.time()
		self.response_time_for_NOWORD = 6.0
		self.utt_for_NOWORD = '＊'
		
	def process(self):
		if self.current_turn == 0:
			chg_theme, theme = self.themeHis.decideNextTheme(None)
		else:
			chg_theme, theme = self.themeHis.decideNextTheme(self.user_impression)
		# システム発話生成
		sys_utt, _, s_len, da = self.env.utterance_selection_softmax(chg_theme, theme, self.agent.Q[self.state])# 発話選択
		self.env.sys_utterance_log.append(sys_utt)
		file_name = 'data/{}/{}_{}'.format(self.user, self.user, str(self.current_turn).zfill(3))
		sys_start = time.time() - self.base_time
		print('sys_start : {:.4}'.format(sys_start))
		self.save_log(sys_utt)
		self.mmd.say(sys_utt)
		self.save_log("*")
		sys_end = time.time() - self.base_time
		print('sys_end : {:.4}'.format(sys_end))

		self.asr.start()
		# rec voice
		self.record.start(file_name)
		# run openface
		if self.mode == "online":
			self.openface.start()
		self.asr.start()
		user_start = None
		while True:
			if (user_start == None) and (self.asr.is_listening == True):
				user_start = time.time() - self.base_time
			if self.asr.is_turn == False:
				user_utt = self.asr.read_result()
				if user_utt == "":
					user_utt = self.utt_for_NOWORD
					print("ユーザ音声が入力されませんでした")
					user_start = sys_end + self.response_time_for_NOWORD
					break
			else:
				time.sleep(0.1)

		self.asr.stop()
		self.record.save_complete = False
		self.record.stop()
		while True:
			if self.record.save_complete == True:
				break
			else:
				time.sleep(1)
				# print("wait")
		if self.mode == "online":
			self.openface.stop()
		self.opensmile.run(file_name)
		self.env.user_utterance_log.append(user_utt)
			
		print('u_start : {}'.format(user_start))
		print('utterance -> {}'.format(user_utt))
		u_start_from_sys_end = user_start - sys_end

		# predict mono modal
		self.d_pred = None
		self.v_pred = None
		self.t_pred = None
		self.f_pred = None
		thread_list = []
		thread_list.append(threading.Thread(\
			target=self.predict_dialogue, args=([user_utt, sys_utt, da, u_start_from_sys_end])))
		thread_list.append(threading.Thread(\
			target=self.predict_voice, args=(["{}.csv".format(file_name)])))
		thread_list.append(threading.Thread(\
			target=self.predict_text, args=([user_utt])))
		thread_list.append(threading.Thread(\
			target=self.predict_face, args=()))
		for thread in thread_list:
			thread.start()
		for thread in thread_list:
			thread.join()

		###### fusion 4 modal #######
		df = pd.DataFrame(data=[[self.d_pred, self.v_pred, self.t_pred, self.f_pred]])
		X_test = df.iloc[0, :].values
		self.user_impression = pf.predUnknown(X_test, 'fusion')
		self.user_impression = pf.changePredValueRange(self.user_impression)# 値のrange変更（試作）

		n_state = self.env.get_next_state(self.user_impression, sys_utt, user_utt)
		self.state = n_state	# 更新

		self.current_turn += 1
		# 終了判定
		if self.current_turn == self.turn_num:
			is_end = True
		else:
			is_end = False
		return is_end
		

	def predict_dialogue(self, user_utt, sys_utt, da, u_start_from_sys_end):
		df = pf.makeDiaDF(u_start_from_sys_end,\
			 len(sys_utt), len(user_utt), u_start_from_sys_end, da)
		X_test = df.iloc[0, :].values
		self.d_pred = pf.predUnknown(X_test, 'dialogue')

	def predict_voice(self, file_name):
		df = pd.read_csv(file_name)
		df = pf.selectVoiceFea(df, case='pred')
		X_test = df.iloc[0, :].values
		self.v_pred = pf.predUnknown(X_test, 'voice')

	def predict_text(self, user_utt):
		df = etf.makeFea(user_utt)
		pca = pickle.load(open('./modelUIpred/pca.model', 'rb'))
		df = pf.PCAonlyBOW(df, pca=pca)
		X_test = df.iloc[0, 1:-1].values
		X_test = X_test.astype(np.float32)
		self.t_pred = pf.predUnknown(X_test, 'text')

	def predict_face(self):
		self.f_pred = np.random.randint(3.5, 4.6)

	def record_log(self, utt):
		def format_time():
			t = datetime.datetime.now()
			s = t.strftime('%Y-%m-%dT%H:%M:%S.%f')
			tail = s[-7:]
			f = round(float(tail), 3)
			temp = "%.3f" % f
			return "%s%s" % (s[:-7], temp[1:])
		elapsed = round(time.time() - self.base_time, 3)
		self.log.append("{}, {}, {}".format(format_time(), elapsed, utt)

	def save_log(self):
		now = datetime.datetime.now()
		fp = "log/{}.csv".format(self.user)
		with open(fp, "w", encoding="utf-8") as f:
			w = csv.writer(f)
			for l in self.log:
				w.writerow(l)

class Record:


	def __init__(self):
		self.is_record = False
		self.save_complete = False

	def start(self, file_name):
		def run(self):
			chunk = 1024
			FORMAT = pyaudio.paInt16
			CHANNELS = 1
			audio = pyaudio.PyAudio()
			RATE = 44100
			# 音の取込開始
			stream = audio.open(format = FORMAT,
				channels = CHANNELS,
				rate = RATE,
				input = True,
				frames_per_buffer = chunk
				)
			# 音データの取得
			data = stream.read(chunk)
			# ndarrayに変換
			x = np.frombuffer(data, dtype="int16") / 32768.0
			frames = []
			# 録音処理
			while self.is_record:
				for i in range(0, int(RATE / chunk * 1)):
					data = stream.read(chunk)
					frames.append(data)
					ndarray = np.frombuffer(data, dtype="int16") / 32768.0
			# 録音終了処理
			stream.stop_stream()
			stream.close()
			audio.terminate()
			# 録音データをファイルに保存
			wav = wave.open(file_name, 'wb')
			wav.setnchannels(CHANNELS)
			wav.setsampwidth(audio.get_sample_size(FORMAT))
			wav.setframerate(RATE)
			wav.writeframes(b''.join(frames))
			wav.close()
			self.save_complete = True

		if file_name.endswith(".wav") == False:
			file_name = file_name + ".wav"
		self.is_record = True
		thread = threading.Thread(target=run, args=(self,))
		thread.start()

	def stop(self):
		self.is_record = False

class OpenSmile:


	def __init__(self):
		path = ""
		with open("refData/path.csv") as f:
			reader = csv.reader(f)
			for row in reader:
				if row[0] == "opensmile":
					path = row[1]
					break
		if path == "":
			raise Exception("opensmile path undefined")
		self.command_common = "{}/bin/Win32/SMILExtract_Release.exe -C {}/config/IS09_emotion.conf > nul"\
			.format(path, path) + " -I {}.wav -O {}.arff"

	def run(self, file_name):
		command = self.command_common.format(file_name, file_name)
		# print("=======================")
		# print(command)
		# print("=======================")
		subprocess.call(command.split(" "), shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		with open("{}.arff".format(file_name) , "r") as inFile:
			content = inFile.readlines()
			new = self.arff_to_csv(content)
		with open("{}.csv".format(file_name), "w") as outFile:
			outFile.writelines(new)

	def arff_to_csv(self, content):
		data = False
		header = ""
		newContent = []
		for line in content:
			if not data:
				if "@attribute" in line:
					attri = line.split()
					columnName = attri[attri.index("@attribute")+1]
					header = header + columnName + ","
				elif "@data" in line:
					data = True
					header = header[:-1]
					header += '\n'
					newContent.append(header)
			else:
				newContent.append(line)
		return newContent

class OpenFace:


	def __init__(self, mode="WebCamera", user="sample"):
		# init
		self.mode = mode
		if self.mode not in ["WebCamera", "online"]:
			raise Exception("openface mode is incorrect")
		self.is_running = False
		self.file_num = 0
		self.ex_num = 0
		self.handle = None
		self.rect = None
		self.user = user
		self.p = None
		# read path
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
		# init command
		if mode == "WebCamera":
			self.command_web = "{}/FeatureExtraction.exe -device 0 -of /openface/{}"\
				.format(openface_path, self.user)
		elif mode == "online":
			self.command_online = "{}/FaceLandmarkImg.exe -f data/{}/file_name -out_dir data/{}/result"\
				.format(openface_path, self.user, self.user)
		# init folder
		while True:
			data_path = "data/{}".format(self.user)
			if os.path.isdir(data_path):
				print("ユーザ「{}」のデータはすでに存在しています．フォルダを消去しますか?"\
					.format(self.user))
				is_delete = input("y/n>>")
				if is_delete == "y":
					shutil.rmtree(data_path)
					time.sleep(0.2)
					os.mkdir(data_path)
					break
				else:
					self.user = input("新しいユーザ名を入力してください>>")
			else:
				os.mkdir(data_path)
				break
		os.mkdir("{}/result".format(data_path))
		# init rect
		if mode == "online":
			self.get_zoom_rect()

	def get_zoom_rect(self):
		# zoomの被験者が映るウィンドウを最前面で固定し，座標を取得する．
		# なぜかこのforループを回さないとウィンドウ位置がずれる
		for m in get_monitors():
			pass
		# 現在アクティブなウィンドウ名を探す
		process_list = []
		def callback(handle, _):
			process_list.append(win32gui.GetWindowText(handle))
		win32gui.EnumWindows(callback, None)
		# ウィンドウ名一覧を表示(デバック用)
		# import pprint
		# pprint.pprint(process_list)
		# Zoomウィンドウを探す
		for process_name in process_list:
			if "VideoFrameWnd" in process_name:
				self.handle = win32gui.FindWindow(None, process_name)
				break
		if self.handle == None:
			raise Exception("Zoom window not found")
		# ウィンドウを最前列で固定
		win32gui.SetWindowPos(self.handle,win32con.HWND_TOPMOST,\
			0,0,0,0,win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
		# ウィンドウの座標を取得
		self.rect = win32gui.GetWindowRect(self.handle)

	def start(self):
		if self.is_running == True:
			print("openface is alrady running")
			return
		if self.mode == "WebCamera":
			self.p = subprocess.Popen(self.command_web)
			self.is_running = True

		elif self.mode == "online":
			def run(self):
				while self.is_running:
					self.online_process()
			thread = threading.Thread(target=run, args=(self,))
			self.is_running = True
			thread.start()
		
	def online_process(self):
		# get screen shot
		file_name = "{}_{}_{}.jpg".format(self.user, self.ex_num, self.file_num)
		self.file_num += 1
		screenshot = ImageGrab.grab()
		croped_screenshot = screenshot.crop(self.rect)
		croped_screenshot.save("data/{}/{}"\
			.format(self.user, file_name))
		# extract landmark
		command = self.command_online.replace("file_name", file_name)
		subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

	def stop(self):
		if self.is_running == False:
			print("openface is not running")
			return
		else:
			self.is_running = False
		if self.mode == "WebCamera":
			self.p.terminate()
		elif self.mode == "online":
			# ウィンドウを最前列で固定を解除
			win32gui.SetWindowPos(self.handle, win32con.HWND_NOTOPMOST, 0,\
				0, 0, 0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
			self.ex_num += 1
			self.file_num = 0

def main():
	nh = NHChat(mode="WebCamera")
	nh.run()
	print("test")
	# openface_test()
	# record_test()

def openface_test():
	of = OpenFace(mode="online")
	of.start()
	start = time.time()
	while True:
		if time.time() - start > 5:
			break
		else:
			time.sleep(0.1)
	of.stop()

def record_test():
	record = Record()
	print("start recording")
	record.start("data/tmp_user_000")
	time.sleep(2)
	record.stop()
	while True:
		if record.save_complete == True:
			break
		else:
			time.sleep(1)
			print("wait")
	print("stop recording")
	
	

if __name__ == "__main__":
	main()