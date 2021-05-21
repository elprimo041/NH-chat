# -*- coding:utf-8 -*-
import time
import csv
import socket
import os
import datetime
import subprocess
from socket import gethostname

import SpeechRecognitionManager
from AbstractCommunicator import AbstractCommunicator
from kill_task import kill_task


class AbstractChat:


	def __init__(self, text = False, ASR_module="Julius"):
		host = "%s" % gethostname()
		self.text = text
		self.is_save_log = True
		self.log = []
		self.utt_num = 1
		self.mmd = MMDAgent()
		if ASR_module == "Julius":
			self.asr = SpeechRecognitionManager.JuliusASR(host, 10500)
		elif ASR_module == "Google":
			print("connect to Google ASR")
			self.asr = SpeechRecognitionManager.GoogleASR()

	def record_log(self, utt_num, spoke, utt):
		self.log.append([utt_num, spoke, utt])

	def save_log(self):
		now = datetime.datetime.now()
		fp = "log/{}.csv".format(now.strftime("%Y%m%d_%H%M%S")) 
		with open(fp, "w", newline="") as f:
			w = csv.writer(f)
			w.writerow(["ex_num", "speaker", "utt"])
			for l in self.log:
				w.writerow(l)
                

	def run(self):
		while True:
			is_end = self.process()
			if is_end == True:
				break
		if self.is_save_log == True:
			self.save_log()
		self.end()

	def end(self):
		self.mmd.end()

	def process(self):
		sys_utt, is_end = self.generate_sys_utt()
		self.mmd.say(sys_utt)
		self.record_log(self.utt_num, "S", sys_utt)
		self.utt_num += 1
		user_utt = self.get_user_utt()
		self.record_log(self.utt_num, "U", user_utt)
		self.utt_num += 1
		self.update_state()
		return is_end

	def get_user_utt(self):
		if self.text:
			user_utt = input("ユーザ発話>>")
		else:
			self.asr.start()
			start_time = time.time()
			while True:
				if self.asr.asr_result != "":
					user_utt = self.asr.read_result()
					break
				elif time.time() - start_time > 5:
					user_utt = ""
					print("ユーザ音声が入力されませんでした")
				else:
					time.sleep(0.1)
		return user_utt

	def update_state(self):
		raise Exception("状態更新関数を定義してください")

	def generate_sys_utt(self):
		raise Exception("システム発話生成関数を定義してください")

class MMDAgent(AbstractCommunicator):


	def __init__(self, log_file="log/{}"):
		host = "%s" % gethostname()
		super(MMDAgent, self).__init__(host, 39390)
		self.debug = True
		kill_task("MMDAgent")
		self.mmd_path = ""
		with open("refData/path.csv") as f:
			reader = csv.reader(f)
			for row in reader:
				if row[0] == "MMDAgent":
					self.mmd_path = row[1]
					break
		if self.mmd_path == "":
			raise Exception("MMDAgent path undefined")
		cmd_run_mmda = "{}/MMDAgent.exe {}/MMDAgent_Example.mdf"\
			.format(self.mmd_path, self.mmd_path)
		# run MMDAgent
		self.p = subprocess.Popen(cmd_run_mmda.split(" "))
		self.printDebug("activate MMDAgent")
		# connect MMdagent server
		start_time = time.time()
		while True:
			try:
				self.start()
			except ConnectionRefusedError:
				pass
			if self.client.connected == True:
				break
			if time.time() - start_time > 15:
				raise Exception("Time Out:MMDAgentとの接続に時間がかかりすぎています")
		self.printDebug("connect to MMDAgent")
		time.sleep(3)
		self.is_speaking = False
		self.base_time = time.time()

		self.speak_start_command_time = None
		self.speak_end_command_time = None


	def printDebug(self, message):
		if self.debug:
			print(message)

	def say(self, speech):
		# self.debug = True
		command =  'SYNTH_START|mei|mei_voice_normal|{}'.format(speech)
		self.is_speaking = True
		print("command send")
		self.sendLine(command, "shift_jis")
		while self.is_speaking:
			pass

	def move(self, motion):
		fp = self.mmd_path + "/" + "Motion" + "/" + motion + "/" + motion + ".vmd"
		if os.path.exists(fp):
			command = "MOTION_ADD|mei|action|" + fp + "|PART|ONCE"
			self.sendLine(command, "shift_jis")
		else:
			print("motion command is not found:{}".format(motion))

	def express(self, expression):
			fp = self.mmd_path + "/" + "Expression" + "/" + expression + "/" + expression + ".vmd"
			if os.path.exists(fp):
				command = "MOTION_ADD|mei|action|" + fp + "|PART|ONCE"
				self.sendLine(command, "shift_jis")
			else:
				print("expression file is not found:{}".format(expression))

	def onReceived(self, message):
		self.printDebug("====================================")
		self.printDebug(message)
		self.printDebug("====================================")
		if "RECOG_EVENT_START" in message:
			self.printDebug("音声認識開始")
		elif "RECOG_EVENT_STOP" in message:
			self.printDebug("音声認識終了")
		elif "SYNTH_EVENT_START" in message:
			self.printDebug("音声合成開始")
			# print("音声合成開始")
			self.speak_start_command_time = time.time()
		elif "SYNTH_EVENT_STOP" in message:
			self.printDebug("音声合成終了")
			# print("音声合成終了")
			self.speak_end_command_time = time.time()
			self.is_speaking = False
		elif "LIPSYNC_EVENT_START" in message:
			self.printDebug("唇開始")
		elif "LIPSYNC_EVENT_STOP" in message:
			self.printDebug("唇終了")
		# elif "MOTION_EVENT_ADD" in message:
		# 	print("動作開始")
		# elif "MOTION_EVENT_CHANGE" in message:
		# 	print("動作変更")
		# elif "MOTION_EVENT_DELETE" in message:
		# 	print("動作終了")
		

	def end(self):
		self.stop()
		self.p.terminate()
		kill_task("MMDAgent")

def main():
	# chat = AbstractChat()
	# chat.end()
	mmd_test()

def mmd_test():
	mmd = MMDAgent("localhost", 39390, 'C:/Users/kaldi/Desktop/MMDAgent/MMDAgent')
	while True:
		speech = input("動作>>")
		if speech == "end":
			mmd.move("mei_bye")
			mmd.say("さようなら")
			time.sleep(2)
			mmd.end()
			break
		elif speech == "say":
			speech = input("システム発話>>")
			mmd.say(speech)
		elif speech == "move":
			motion = input("モーション>>")
			mmd.move(motion)
	

if __name__ == "__main__":
	main()