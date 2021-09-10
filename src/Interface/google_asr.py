# -*- coding:utf-8 -*-
# 参考(というかコピペ元)サイト
# https://github.com/googleapis/python-speech/blob/d6a206ad176358d045e129e97c26b65be13b70a2/samples/microphone/transcribe_streaming_infinite.py

import sys
import time
import wave
import matplotlib.pyplot as plt
import numpy as np


from google.cloud import speech
import pyaudio
from six.moves import queue

from manage_turn import ManageTurn

# Audio recording parameters
STREAMING_LIMIT = 4 * 60 * 1000  # 4 minutes
SAMPLE_RATE = 16000
CHUNK_SIZE = int(SAMPLE_RATE / 10)  # 100ms


def get_current_time():
    """Return Current Time in MS."""

    return int(round(time.time() * 1000))


class ResumableMicrophoneStream:
    """Opens a recording stream as a generator yielding the audio chunks."""

    def __init__(self, rate, chunk_size, is_debug=False, file_num=0):
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
        self._format = pyaudio.paInt16
        self._audio_stream = self._audio_interface.open(
            format=self._format,
            channels=self._num_channels,
            rate=self._rate,
            input=True,
            frames_per_buffer=self.chunk_size,
            # Run the audio stream asynchronously to fill the buffer object.
            # This is necessary so that the input device's buffer doesn't
            # overflow while the calling thread makes network requests, etc.
            stream_callback=self._fill_buffer,
        )

        self.debug = is_debug
        self.file_name = "googleASR_{}".format(file_num)
        self.data_all = []

    def print_debug(self, message):
        if(self.debug):
            print(message)

    def set_debug(self, debug):
        self.debug = debug

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

        if self.debug:
            # waveファイルの保存
            wavFile = wave.open("{}.wav".format(self.file_name), 'wb')
            wavFile.setnchannels(self._num_channels)
            wavFile.setsampwidth(
                self._audio_interface.get_sample_size(self._format))
            wavFile.setframerate(SAMPLE_RATE)
            joined_data = b"".join(self.data_all)
            wavFile.writeframes(joined_data)
            wavFile.close()
            self.print_debug("save {}".format(self.file_name))

            # 波形画像の保存
            wave_result = np.frombuffer(
                joined_data, dtype="int16") / float(2**15)
            plt.plot(wave_result)
            plt.savefig("{}.png".format(self.file_name))

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

                    chunks_from_ms = round(
                        (self.final_request_end_time - self.bridging_offset)
                        / chunk_time
                    )

                    self.bridging_offset = round(
                        (len(self.last_audio_input) - chunks_from_ms) * chunk_time
                    )

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
            self.data_all.append(chunk)
            # Now consume whatever other data's still buffered.
            while True:
                try:
                    chunk = self._buff.get(block=False)

                    if chunk is None:
                        return
                    data.append(chunk)
                    self.data_all.append(chunk)
                    self.audio_input.append(chunk)

                except queue.Empty:
                    break
            yield b"".join(data)


class GoogleASR:
    """
    Google Speech to Textで音声認識を行うクラス
    ターンテイキングにはmanage_turn.MnageTurnを用いる
    使用には認証ファイルの取得が必要
    https://cloud.google.com/speech-to-text/docs/libraries?hl=ja
    """

    def __init__(self, response_time_no_word, turn_buffer, is_debug=False):
        self.debug = is_debug
        self.file_num = 0
        self.m_turn = ManageTurn(self, response_time_no_word=response_time_no_word,
                                 turn_buffer=turn_buffer, is_debug=is_debug)
        self.is_listening = False
        self.recognition_result = ""
        # ユーザのターンが始まり音声認識を開始した時刻
        # 相対時間ではなく時刻
        self.turn_start_time = None

        # ユーザのターンが始まってから初めてユーザ発話を認識するまでの時間
        # 時刻ではなく，経過時間
        # ユーザ発話開始時刻 - ユーザのターン開始時刻(self.turn_start_time)
        self.utt_start_time = None

        # ユーザの音声認識結果が確定した時刻
        # ターンテイキングで使う
        # 相対時間ではなく時刻
        self.recognition_confirmed_time = None
        self.stream = None
        self.base_time = time.time()

    def set_debug(self, debug):
        self.debug = debug

    def print_debug(self, message):
        if(self.debug):
            elapsed = time.time() - self.base_time
            elapsed = round(elapsed, 2)
            print("[{}]:{}".format(elapsed, message))

    def listen_loop(self, responses):
        for response in responses:
            self.print_debug(response)
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
            result_micros = 0

            if result.result_end_time.seconds:
                result_seconds = result.result_end_time.seconds

            if result.result_end_time.microseconds:
                result_micros = result.result_end_time.microseconds

            self.stream.result_end_time = int(
                (result_seconds * 1000) + (result_micros / 1000))

            if result.is_final:
                # 音声認識結果が確定
                self.print_debug("ASR:{}".format(transcript))
                self.is_listening = False
                self.print_debug("end listening")
                self.recognition_confirmed_time = time.time()
                self.recognition_result += transcript
                self.stream.is_final_end_time = self.stream.result_end_time
                self.stream.last_transcript_was_final = True

            else:
                if self.is_listening == False:
                    # 音声認識開始
                    self.is_listening = True
                    self.print_debug("start listening")
                self.stream.last_transcript_was_final = False

    def start(self, auto_turn=True, reset_result=False):
        # auto_turnがTrueの場合自動でターンテイキングを行う
        # 基本的にはTrueで良い
        self.print_debug("start Google ASR")
        if reset_result == True:
            self.recognition_result = ""
        self.is_listening = False
        self.utt_start_time = None
        self.turn_start_time = time.time()
        turn_thread_flag = False
        client = speech.SpeechClient()
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=SAMPLE_RATE,
            language_code="ja-JP",
            max_alternatives=1,)
        # streaming_config = speech.StreamingRecognitionConfig(
        #     config=config, interim_results=True)
        # single_utterance設定をオン
        # オンにしないと音声認識結果が確定するまで60秒かかる
        streaming_config = speech.StreamingRecognitionConfig(
            config=config, interim_results=True, single_utterance=True)
        mic_manager = ResumableMicrophoneStream(SAMPLE_RATE, CHUNK_SIZE)
        with mic_manager as self.stream:
            while not self.stream.closed:
                self.stream.audio_input = []
                audio_generator = self.stream.generator()
                requests = (
                    speech.StreamingRecognizeRequest(audio_content=content)
                    for content in audio_generator
                )

                if (turn_thread_flag == False) and (auto_turn == True):
                    turn_thread_flag = True
                    self.m_turn.start_turn_thread()

                responses = client.streaming_recognize(
                    streaming_config, requests)

                # 音声認識結果を取得するループ開始
                self.listen_loop(responses)

                # streamリミットを超えた場合の音声認識再開処理
                # 4分stream繋ぎ続けない限り実行されない
                if self.stream.result_end_time > 0:
                    self.stream.final_request_end_time = self.stream.is_final_end_time
                self.stream.result_end_time = 0
                self.stream.last_audio_input = []
                self.stream.last_audio_input = self.stream.audio_input
                self.stream.audio_input = []
                self.stream.restart_counter = self.stream.restart_counter + 1

                if not self.stream.last_transcript_was_final:
                    sys.stdout.write("\n")
                self.stream.new_stream = True
        self.file_num += 1

    def stop(self):
        self.print_debug("stop Google ASR")
        self.stream.closed = True

    def end(self):
        pass

    def get_utt_start_time(self):
        # ユーザ発話がなかった場合はresponse_time_no_wordを返す
        if self.utt_start_time == None:
            self.utt_start_time = self.m_turn.response_time_no_word
        return self.utt_start_time

    def read_result(self):
        result = self.recognition_result
        self.recognition_result = ""
        return result


def google_test():
    google = GoogleASR(response_time_no_word=6, turn_buffer=1.5, is_debug=True)
    for i in range(1):
        print("turn {}".format(i+1))
        google.start()
        while not google.m_turn.is_sys_turn_end:
            time.sleep(0.1)
        print("ASR result:{}".format(google.read_result()))


def main():
    google_test()


if __name__ == "__main__":

    main()
