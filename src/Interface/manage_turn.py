# -*- coding:utf-8 -*-
import time
import threading


class ManageTurn:

    def __init__(self, asr, response_time_no_word, turn_buffer, is_debug=False):
        """
        ターンテイキングのルールを規定する．
        julius_asr.JuliusASRかgoogle_asr.GoogleASRのインスタンスを引数で受け取る．

        Parameters
        ----------
        asr : instance
            JuliusASRかgoogleASRのインスタンスを渡す(ManageTurn(self)の形)
        response_time_no_word : float
            ユーザターン開始後(response_time_no_word)秒ユーザが発話しない場合
            ターンテイキング

        turn_buffer : float
            音声認識確定後(turn_buffer)秒ユーザが発話しない場合ターンテイキング
        is_debug : bool, optional
            default False
        """
        self.debug = is_debug
        self.asr = asr
        self.response_time_no_word = response_time_no_word
        self.turn_buffer = turn_buffer
        self.is_sys_turn_end = False

    def set_debug(self, debug):
        self.debug = debug

    def print_debug(self, message):
        if(self.debug):
            print(message)

    def start_turn_thread(self):
        # turn_take_simple_ruleをスレッドで実行しターンの終了を判定
        # スレッド内でターン終了を判定しasr.stopを実行
        self.is_sys_turn_end = False
        thread = threading.Thread(target=self.turn_take_simple_rule)
        thread.start()

    def turn_take_simple_rule(self):
        """
        無音で一定時間(response_time_no_word)経過
        or
        音声認識確定から一定時間(turn_buffer)経過
        でターンテイキング

        ターン開始時刻：self.asr.turn_start_time
        ターン開始からの経過時間：elapsed_from_start
        音声認識確定時刻：self.asr.recognition_confirmed_time
        音声認識確定からの経過時間：elapsed_from_conf
        初ユーザ発話開始時のターン開始からの経過時間：asr.utt_start_time
        """
        while True:
            if self.asr.utt_start_time == None and self.asr.is_listening == True:
                self.asr.utt_start_time = time.time() - self.asr.turn_start_time

            elapsed_from_start = time.time() - self.asr.turn_start_time
            if self.asr.recognition_confirmed_time == None:
                elapsed_from_conf = 0
            else:
                elapsed_from_conf = time.time() - self.asr.recognition_confirmed_time
            # 無音で一定時間(response_time_no_word)経過でターンテイキング
            if elapsed_from_start > self.response_time_no_word \
                    and self.asr.recognition_result == "" \
                    and self.asr.is_listening == False:
                self.print_debug("### turn: no word ###")
                break
            # 音声認識確定から一定時間(turn_buffer)経過でターンテイキング
            elif elapsed_from_conf > self.turn_buffer \
                    and self.asr.recognition_result != "" \
                    and self.asr.is_listening == False:
                break
            time.sleep(0.1)
        self.asr.stop()
        self.print_debug("### End user turn ###")
        self.is_sys_turn_end = True
