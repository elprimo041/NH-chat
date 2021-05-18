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

# uses result_end_time currently only avaialble in v1p1beta, will be in v1 soon
from google.cloud import speech_v1p1beta1 as speech
import pyaudio
from six.moves import queue

from kill_task import kill_task


# Audio recording parameters
STREAMING_LIMIT = 10000
SAMPLE_RATE = 16000
CHUNK_SIZE = int(SAMPLE_RATE / 10)  # 100ms

# RED = '\033[0;31m'
# GREEN = '\033[0;32m'
# YELLOW = '\033[0;33m'

def get_current_time():
	"""Return Current Time in MS."""

	return int(round(time.time() * 1000))

class ResumableMicrophoneStream:
	"""Opens a recording stream as a generator yielding the audio chunks."""

	def __init__(self, rate, chunk_size):
		self._rate = rate
		self.chunk_size = chunk_size
		self._num_channels = 1
		self._buff = queue.Queue()
		self.closed = True
		self.start_time = get_current_time()
		self.restart_counter = 0
		self.audio_input = []
		self.last_audio_input = []
		self.result_end_time = 0
		self.is_final_end_time = 0
		self.final_request_end_time = 0
		self.bridging_offset = 0
		self.last_transcript_was_final = False
		self.new_stream = True
		self._audio_interface = pyaudio.PyAudio()
		self._audio_stream = self._audio_interface.open(
			format=pyaudio.paInt16,
			channels=self._num_channels,
			rate=self._rate,
			input=True,
			frames_per_buffer=self.chunk_size,
			# Run the audio stream asynchronously to fill the buffer object.
			# This is necessary so that the input device's buffer doesn't
			# overflow while the calling thread makes network requests, etc.
			stream_callback=self._fill_buffer,
		)

	def __enter__(self):

		self.closed = False
		return self

	def __exit__(self, type, value, traceback):

		self._audio_stream.stop_stream()
		self._audio_stream.close()
		self.closed = True
		# Signal the generator to terminate so that the client's
		# streaming_recognize method will not block the process termination.
		self._buff.put(None)
		self._audio_interface.terminate()

	def _fill_buffer(self, in_data, *args, **kwargs):
		"""Continuously collect data from the audio stream, into the buffer."""

		self._buff.put(in_data)
		return None, pyaudio.paContinue

	def generator(self):
		"""Stream Audio from microphone to API and to local buffer"""

		while not self.closed:
			data = []

			if self.new_stream and self.last_audio_input:

				chunk_time = STREAMING_LIMIT / len(self.last_audio_input)

				if chunk_time != 0:

					if self.bridging_offset < 0:
						self.bridging_offset = 0

					if self.bridging_offset > self.final_request_end_time:
						self.bridging_offset = self.final_request_end_time

					chunks_from_ms = round((self.final_request_end_time -
											self.bridging_offset) / chunk_time)

					self.bridging_offset = (round((
						len(self.last_audio_input) - chunks_from_ms)
												  * chunk_time))

					for i in range(chunks_from_ms, len(self.last_audio_input)):
						data.append(self.last_audio_input[i])

				self.new_stream = False

			# Use a blocking get() to ensure there's at least one chunk of
			# data, and stop iteration if the chunk is None, indicating the
			# end of the audio stream.
			chunk = self._buff.get()
			self.audio_input.append(chunk)

			if chunk is None:
				return
			data.append(chunk)
			# Now consume whatever other data's still buffered.
			while True:
				try:
					chunk = self._buff.get(block=False)

					if chunk is None:
						return
					data.append(chunk)
					self.audio_input.append(chunk)

				except queue.Empty:
					break

			yield b''.join(data)

class GoogleASR:
	"""
	音声認識サーバに接続するクラス
	"""

	def __init__(self):
		self.recognitionResult = ""
		self.recognitionResult_all = ""
		self.is_listening = False
		self.is_turn = False
		self.recognition_confirmed_time = get_current_time()
		self.threshold = 1
		
		
	def start(self):
		self.is_turn = True
		speak_end_time = Value('d', get_current_time())
		is_speak = Value("b", False)
		self.recognition_confirmed_time = get_current_time()
		t_main = threading.Thread(target=self.speech_recognition, args=([speak_end_time, is_speak]))
		t_turn = threading.Thread(target=self.turn_end)
		t_turn.setDaemon(True)
	
		t_main.start()
		t_turn.start()

	def stop(self):
		self.is_turn = False
		
	def read_result(self):
		tmp = ""
		if (self.recognitionResult != ""):
			tmp = self.recognitionResult
			self.recognitionResult = ""   
		return tmp
	
	def listen_print_loop(self, responses):
		"""Iterates through server responses and prints them.
		The responses passed is a generator that will block until a response
		is provided by the server.
		Each response may contain multiple results, and each result may contain
		multiple alternatives; for details, see https://goo.gl/tjCPAU.  Here we
		print only the transcription for the top alternative of the top result.
		In this case, responses are provided for interim results as well. If the
		response is an interim one, print a line feed at the end of it, to allow
		the next result to overwrite it, until the response is a final one. For the
		final one, print a newline to preserve the finalized transcription.
		"""
	
		for response in responses:
	
			if get_current_time() - self.stream.start_time > STREAMING_LIMIT:
				self.stream.start_time = get_current_time()
				break
	
			if not response.results:
				continue
	
			result = response.results[0]
	
			if not result.alternatives:
				continue
	
			transcript = result.alternatives[0].transcript
	
			result_seconds = 0
			result_nanos = 0
	
			if result.result_end_time.seconds:
				result_seconds = result.result_end_time.seconds
	
			if result.result_end_time.nanos:
				result_nanos = result.result_end_time.nanos
	
			self.stream.result_end_time = int((result_seconds * 1000)
										 + (result_nanos / 1000000))
	
			corrected_time = (self.stream.result_end_time - self.stream.bridging_offset
							  + (STREAMING_LIMIT * self.stream.restart_counter))
			# Display interim results, but with a carriage return at the end of the
			# line, so subsequent lines will overwrite them.
	
			if result.is_final:
				self.is_listening = False
				self.recognition_confirmed_time = get_current_time()
				self.recognitionResult_all += transcript
				
				if self.is_turn == True:
					self.recognitionResult += transcript
				
				# sys.stdout.write(GREEN)
				# sys.stdout.write('\033[K')
				# sys.stdout.write(str(corrected_time) + ': ' + transcript + '\n')
	
				self.stream.is_final_end_time = self.stream.result_end_time
				self.stream.last_transcript_was_final = True
	
				# Exit recognition if any of the transcribed phrases could be
				# one of our keywords.
				# if re.search(r'\b(exit|quit)\b', transcript, re.I):
				# 	sys.stdout.write(YELLOW)
				# 	sys.stdout.write('Exiting...\n')
				# 	self.stream.closed = True
				# 	break
	
			else:
				self.is_listening = True
				# sys.stdout.write(RED)
				# sys.stdout.write('\033[K')
				# sys.stdout.write(str(corrected_time) + ': ' + transcript + '\r')
	
				self.stream.last_transcript_was_final = False

	def speech_recognition(self, speak_end_time, is_speak):
		"""start bidirectional streaming from microphone input to speech API"""
	
		client = speech.SpeechClient()
		config = speech.types.RecognitionConfig(
			encoding=speech.enums.RecognitionConfig.AudioEncoding.LINEAR16,
			sample_rate_hertz=SAMPLE_RATE,
			language_code='ja-JP',
			max_alternatives=1)
		streaming_config = speech.types.StreamingRecognitionConfig(
			config=config,
			interim_results=True)
	
		mic_manager = ResumableMicrophoneStream(SAMPLE_RATE, CHUNK_SIZE)
		# print(mic_manager.chunk_size)
		# sys.stdout.write(YELLOW)
		# sys.stdout.write('\nListening, say "Quit" or "Exit" to stop.\n\n')
		# sys.stdout.write('End (ms)       Transcript Results/Status\n')
		# sys.stdout.write('=====================================================\n')
	
		with mic_manager as self.stream:
	
			while not self.stream.closed:
				# sys.stdout.write(YELLOW)
				# sys.stdout.write('\n' + str(
				#     STREAMING_LIMIT * self.stream.restart_counter) + ': NEW REQUEST\n')
	
				self.stream.audio_input = []
				audio_generator = self.stream.generator()
	
				requests = (speech.types.StreamingRecognizeRequest(
					audio_content=content)for content in audio_generator)
	
				responses = client.streaming_recognize(streaming_config,
													   requests)
	
				# Now, put the transcription responses to use.
				is_speak.value = True
				self.listen_print_loop(responses)
				is_speak.value = False
				speak_end_time.value = get_current_time()
				# print("speak end time が更新：{}".format(speak_end_time.value))
	
				if self.stream.result_end_time > 0:
					self.stream.final_request_end_time = self.stream.is_final_end_time
				self.stream.result_end_time = 0
				self.stream.last_audio_input = []
				self.stream.last_audio_input = self.stream.audio_input
				self.stream.audio_input = []
				self.stream.restart_counter = self.stream.restart_counter + 1
	
				# if not self.stream.last_transcript_was_final:
					# sys.stdout.write('\n')
				self.stream.new_stream = True


	def turn_end(self):
		while True:
			elapsed = get_current_time() - self.recognition_confirmed_time
			if self.recognitionResult != "":
				if (elapsed > self.threshold * 1000) and (self.is_listening == False):
					if self.is_turn == True:
						# print("turn taking")
						self.is_turn = False
						break
						
			elif self.recognitionResult == "" and self.is_listening == False:
				if (elapsed > self.threshold * 5000):
					if self.is_turn == True:
						print("turn taking no signal")
						print("elapsed:{}".format(elapsed))
						self.is_turn = False
						break
			else:
				time.sleep(0.1)

class JuliusASR:


	def __init__(self, hostname, port):
		# init
		kill_task("julius.exe")
		self.is_listening = False
		self.msg_stock = ""
		self.recognitionResult = ""
		# read path	
		path = ""
		with open("refData/path.csv") as f:
			reader = csv.reader(f)
			for row in reader:
				if row[0] == "dictation":
					path = row[1]
					break
		if path == "":
			raise Exception("Julius path undefined")
		os.chdir(path)
		# activate julius
		cmd_run_julius = "run-gmm > nul"
		print('#### Julius ASR:Initiating start ####')
		self.p = subprocess.Popen(cmd_run_julius, shell=True)
		time.sleep(5)
		print('#### Julius ASR:Initiating Done ####')
		super(JuliusASR, self).__init__(hostname, port)

	def start(self):
		super().start()
		self.is_listening = True
		
	def stop(self):
		self.is_listening = False

	def end(self):
		super().stop()
		self.p.kill()
		kill_task("julius")

	def read_result(self):
		result = self.recognitionResult
		self.recognitionResult = ""
		return result

	def onReceived(self, message):
		if self.is_listening == False:
			return
		else:
			if len(message) > 1:
				
				self.msg_stock, ts = self.XMLparser(self.msg_stock, message)
				if ts != None:
					self.recognitionResult += ts.word
					print('word:', ts.word)
					# print('time:', ts.us_time)
					self.recognitionResult += ts.word

	def XMLparser(self, msg_stock, msg):
		msg_stock += msg
		msg_list = msg_stock.split('</RECOGOUT>')

		if len(msg_list) >= 2:
			ts = userUtteranceInfo()
			xmlString = msg_list[0].split('\n')
			xmlString = [x for x in xmlString if '=' in x]
			dicList = []
			for line in xmlString:
				dic = self.makeTSdic(line)
				dicList.append(dic)
			for d in dicList:
				if 'STARTREC' in d.values() and 'TIME' in d.keys():
					ts.setTime(int(d['TIME']))
				if 'WORD' in d.keys():
					ts.addWord(d['WORD'])

			msg_stock = ''.join(msg_list[1:])
			
			return msg_stock, ts
		else:
			msg_stock = ''.join(msg_list[:])
			return msg_stock, None

	# str -> dict
	def makeTSdic(self, xmlstr):
		retstr = xmlstr.split(' ')
		retstr = [x for x in retstr if x != '']
		retstr = ' '.join(retstr)
		retstr = retstr.replace('<>', '')
		retstr = retstr.translate(str.maketrans({'<': None, '"': None, '>': None, '/': None}))
		retstr = re.split('[ =]', retstr)
		Dict = {}
		for i, val in enumerate(retstr):
			if val == 'STATUS':
				Dict['STATUS'] = retstr[i+1]
			elif val == 'TIME':
				Dict['TIME'] = retstr[i+1]
			elif val == 'WORD':
				Dict['WORD'] = retstr[i+1]

		return Dict

class userUtteranceInfo:
	def __init__(self):
		self.us_time = None
		self.word = None

	def addWord(self, msg):
		if self.word != None:
			self.word += msg
		else:
			self.word = msg

	def setWord(self, msg):
		self.word = msg
		
	def setTime(self, time):
		self.us_time = time

def julius_test():
	from socket import gethostname
	host = "%s" % gethostname()
	
	julius = JuliusASR(host, 10500)
	julius.start()
	start = time.time()
	while True:
		if time.time() - start > 15:
			break
		else:
			time.sleep(0.1)
	julius.stop()
	julius.end()

def google_test():
	g = GoogleASR()

def main():
	google_test()
	
	
	

if __name__ == "__main__":
	main()

