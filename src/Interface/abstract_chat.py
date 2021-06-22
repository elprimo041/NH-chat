# -*- coding:utf-8 -*-
import time
import csv
import datetime
import os

from tools import MMDAgent
from julius_asr import JuliusASR
from google_asr import GoogleASR


class AbstractChat:
    """
    対話システムのベースとなる抽象クラス．
    ルールベースシステムでも強化学習システムでもこのクラスを継承する．
    """

    def __init__(self, response_time_no_word=6.0, turn_buffer=1.5, text=False,
                 asr_module="julius", is_debug=False, turn_num=3, is_save_log=True):
        self.debug = is_debug
        self.text = text
        self.is_save_log = is_save_log
        self.turn_num = turn_num
        self.log = []
        self.utt_num = 1
        self.current_turn = 1
        self.header = ["ex_num", "speaker", "utt"]
        if self.text == False:
            self.mmd = MMDAgent()
            if asr_module == "julius":
                self.asr = JuliusASR(response_time_no_word=response_time_no_word, 
                                    turn_buffer=turn_buffer, is_debug=is_debug)
            elif asr_module == "google":
                self.asr = GoogleASR(response_time_no_word=response_time_no_word, 
                                    turn_buffer=turn_buffer, is_debug=is_debug)
            else:
                print("音声認識モジュールの名前が誤っています:{}".format(asr_module))
                print("以下から選択してください\njulius, Google")
                raise Exception()

    def __del__(self):
        self.end()

    def set_debug(self, debug):
        self.debug = debug

    def print_debug(self, message):
        if(self.debug):
            print(message)

    def record_log(self, content):
        """
        対話ログを記録する
        ----------
        content : list
            対話ログ
        """
        self.log.append(content)

    def save_log(self, fp=""):
        if fp == "":
            now = datetime.datetime.now()
            fp = "../../user_data/{0}/{0}.csv".format(now.strftime("%Y%m%d_%H%M%S"))
            data_path = "../../user_data/{0}/".format(now.strftime("%Y%m%d_%H%M%S"))
        os.mkdir(data_path) 
        with open(fp, "w", newline="", encoding="shift-jis") as f:
            w = csv.writer(f)
            if self.header != None:
                w.writerow(self.header)
            for l in self.log:
                w.writerow(l)
                

    def run(self):
        while True:
            if self.text == True:
                is_end = self.process_text()
            else:
                is_end = self.process()
            if is_end == True:
                break
        if self.is_save_log == True:
            self.save_log()
        self.end()

    def end(self):
        if self.text == False:
            self.mmd.end()
            self.asr.end()

    def process(self):
        sys_utt, is_end = self.generate_sys_utt()
        self.mmd.say(sys_utt)
        self.record_log([self.utt_num, "S", sys_utt])
        self.utt_num += 1
        user_utt = self.get_user_utt()
        self.record_log([self.utt_num, "U", user_utt])
        self.utt_num += 1
        self.current_turn += 1
        return is_end
    
    def process_text(self):
        sys_utt, is_end = self.generate_sys_utt()
        print("system:{}".format(sys_utt))
        self.record_log([self.utt_num, "S", sys_utt])
        self.utt_num += 1
        user_utt = self.get_user_utt()
        self.record_log([self.utt_num, "U", user_utt])
        self.utt_num += 1
        self.current_turn += 1
        return is_end
        

    def get_user_utt(self):
        if self.text:
            user_utt = input("ユーザ発話>>")
        else:
            self.asr.start()
            while not self.asr.m_turn.is_sys_turn_end:
                time.sleep(0.1)
            user_utt = self.asr.read_result()
            if user_utt == "":
                self.print_debug("ユーザ音声が入力されませんでした")
            else:
                self.print_debug("ASR:{}".format(user_utt))
        return user_utt

    def generate_sys_utt(self):
        # ここではテスト用発話を生成
        # 実際に使用する場合はgenerate_sys_uttをオーバーライド
        # NH-chatではprocessごとオーバーライドしている
        is_end = False
        if self.current_turn == self.turn_num:
            is_end = True
        sys_utt = "テスト用システム発話{}".format(self.current_turn)
        self.print_debug("generate sys utt:{}".format(sys_utt))
        self.print_debug("is end:{}".format(is_end))
        return sys_utt, is_end
        

def main():
    chat_test()

def chat_test():
    chat = AbstractChat(is_debug=True)
    chat.run()
    

if __name__ == "__main__":
    main()