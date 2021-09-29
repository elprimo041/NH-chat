# -*- coding:utf-8 -*-
import re
import time
import subprocess
import sys
from socket import gethostname

from abstract_communicator import AbstractCommunicator
from manage_task import ManageTask
from manage_turn import ManageTurn
from nh_path import NHPath


class JuliusASR(AbstractCommunicator):
    """
    Juliusで音声認識を行うクラス
    ターンテイキングにはmanage_turn.MnageTurnを用いる
    """

    def __init__(self, response_time_no_word, turn_buffer, is_debug=False):
        # init
        host = "%s" % gethostname()
        port = 10500
        self.debug = is_debug
        self.m_task = ManageTask()
        self.m_task.kill_task("julius.exe")
        self.m_turn = ManageTurn(self, response_time_no_word=response_time_no_word,
                                 turn_buffer=turn_buffer, is_debug=is_debug)

        self.is_listening = False
        self.msg_stock = ""
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

        # read path
        nh_path = NHPath()
        try:
            julius_path = nh_path.path["julius"]
        except KeyError:
            print("Julius path undefined")
            sys.exit()

        # activate julius
        cmd = "start /min {0}/bin/windows/julius.exe -C {0}/main.jconf \
                -C {0}/am-gmm.jconf -module > nul".format(julius_path)
        self.print_debug("command julius:\n{}".format(cmd))
        print('#### Julius ASR:Initiating start ####')
        print("### 最初の1発話は上手く認識できません ###")
        self.proc = subprocess.Popen(cmd, shell=True)
        # 起動待ち
        # juliusの標準出力を受け取れたら固定長のsleepではなく起動し次第
        # 次の処理を実行できるが，標準出力が上手く受け取れないので固定sleep
        # 5秒はかなり余裕を持った時間
        time.sleep(5)
        print('#### Julius ASR:Initiating Done ####')
        super(JuliusASR, self).__init__(host, port)

    def __del__(self):
        self.proc.kill()
        self.m_task.kill_task("julius")

    def set_debug(self, debug):
        self.debug = debug

    def print_debug(self, message):
        if(self.debug):
            print(message)

    def start(self, auto_turn=True, reset_result=False):
        self.print_debug("start Julius ASR")
        super().start()
        # init
        self.msg_stock = ""
        if reset_result == True:
            self.recognition_result = ""
        self.is_listening = False
        self.turn_start_time = time.time()
        self.utt_start_time = None
        if auto_turn == True:
            self.m_turn.start_turn_thread()

    def stop(self):
        self.print_debug("stop Julius ASR")
        super().stop()

    def end(self):
        super().stop()
        self.proc.kill()
        self.m_task.kill_task("julius")

    def get_utt_start_time(self):
        # ユーザ発話がなかった場合はresponse_time_no_wordを返す
        if self.utt_start_time == None:
            self.utt_start_time = self.m_turn.response_time_no_word
        return self.utt_start_time

    def read_result(self):
        result = self.recognition_result
        self.recognition_result = ""
        return result

    def on_received(self, message):
        if len(message) > 1:
            if 'INPUT STATUS="STARTREC"' in message:
                # 音声認識開始
                self.is_listening = True
                self.print_debug("start listening")
            elif 'INPUT STATUS="ENDREC"' in message:
                # 音声認識結果が確定
                self.is_listening = False
                self.print_debug("end listening")
                self.recognition_confirmed_time = time.time()
            self.msg_stock, ts = self.xml_parser(self.msg_stock, message)
            if ts != None:
                self.recognition_result += ts.word
                self.print_debug("ASR:{}".format(ts.word))

    def xml_parser(self, msg_stock, msg):
        msg_stock += msg
        msg_list = msg_stock.split('</RECOGOUT>')

        if len(msg_list) >= 2:
            ts = userUtteranceInfo()
            xmlString = msg_list[0].split('\n')
            xmlString = [x for x in xmlString if '=' in x]
            dic_list = []
            for line in xmlString:
                dic = self.make_ts_dic(line)
                dic_list.append(dic)
            for d in dic_list:
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
    def make_ts_dic(self, xmlstr):
        retstr = xmlstr.split(' ')
        retstr = [x for x in retstr if x != '']
        retstr = ' '.join(retstr)
        retstr = retstr.replace('<>', '')
        retstr = retstr.translate(str.maketrans(
            {'<': None, '"': None, '>': None, '/': None}))
        retstr = re.split('[ =]', retstr)
        dict = {}
        for i, val in enumerate(retstr):
            if val == 'STATUS':
                dict['STATUS'] = retstr[i+1]
            elif val == 'TIME':
                dict['TIME'] = retstr[i+1]
            elif val == 'WORD':
                dict['WORD'] = retstr[i+1]
        return dict


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
    julius = JuliusASR(response_time_no_word=6, turn_buffer=1.5, is_debug=True)
    julius.m_turn.set_debug(True)
    for i in range(3):
        print("turn {}".format(i+1))
        julius.start()
        while not julius.m_turn.is_sys_turn_end:
            time.sleep(0.1)
        print("ASR result:{}".format(julius.read_result()))
    julius.end()


def main():
    julius_test()


if __name__ == "__main__":
    main()
