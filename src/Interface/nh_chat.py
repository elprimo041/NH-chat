# -*- coding:utf-8 -*-
import time
import pandas as pd
import pickle
import numpy as np
import time
import datetime
import csv
import shutil
from argparse import ArgumentParser
import warnings
warnings.filterwarnings("ignore")
# RLをパスに追加
import os
import sys
sys.path.append(os.path.join(os.getcwd(), "../RL"))

from abstract_chat import AbstractChat
from tools import Record, OpenSmile, OpenFace
import extFaceFea as eff
import extTextFea as etf
import predUI as pf
from theme import HistoryTheme
from dialogue_env import DialogueEnv
from agent import TrainedQlearningAgent


class NHChat(AbstractChat):


    def __init__(self, model="200117_c099", mode="WebCamera", user="tmp_user", 
                 turn_num=3, text=True, asr_module="google", is_debug=False,
                 response_time_no_word=6.0, turn_buffer=1.5):
        self.debug = is_debug
        super().__init__(response_time_no_word=response_time_no_word, 
                         turn_buffer=turn_buffer, text=text, 
                         asr_module=asr_module, is_debug=is_debug)
        self.env = DialogueEnv()
        if self.text == False:
            self.record = Record(is_debug=is_debug)
            self.opensmile = OpenSmile(is_debug=is_debug)
            self.openface = OpenFace(mode=mode, is_debug=is_debug)
        Qtable_name = "../refData/RL_files/{}/{}_Q".format(model, model)
        self.log_name = "../refData/RL_files/{}/{}_log.csv"\
                            .format(model, model)
        self.agent = TrainedQlearningAgent(Qtable_name)
        self.agent.fillQ(self.env)
        self.state = self.env.reset()
        self.themeHis = HistoryTheme()
        self.model = model
        self.mode = mode
        self.asr_module = asr_module
        self.turn_num = turn_num
        self.user = user
        self.current_turn = 0
        self.user_impression = None
        # init folder
        # すでにユーザデータがある場合，消去するかユーザ名を変更する
        while True:
            self.data_path = "../../user_data/{}".format(self.user)
            if os.path.isdir(self.data_path):
                print("ユーザ「{}」のデータはすでに存在しています．"
                    "フォルダを消去しますか?".format(self.user))
                is_delete = input("y/n>>")
                if is_delete == "y":
                    shutil.rmtree(self.data_path)
                    time.sleep(0.2)
                    break
                else:
                    self.user = input("新しいユーザ名を入力してください>>")
            else:
                break
        os.mkdir(self.data_path)
        os.mkdir("{}/voice".format(self.data_path))
        if self.text == False:
            self.openface.start("{}/{}_face.csv".format(self.data_path, self.user))
        self.base_time = time.time()

    def __del__(self):
        try:
            self.record.stop()
        except AttributeError:
            pass
        try:
            self.openface.stop()
        except AttributeError:
            pass
        self.end()
        
    def set_debug(self, debug):
        self.debug = debug

    def print_debug(self, message):
        if(self.debug):
            print(message)    
        
    def process(self):
        chg_theme, theme = self.themeHis.decideNextTheme(self.user_impression)
        # システム発話生成
        sys_utt, da = self.env.utterance_selection_softmax(\
            chg_theme, theme, self.agent.Q[self.state])
        # 発話選択
        self.env.sys_utterance_log.append(sys_utt)
        file_name = "../../user_data/{0}/voice/{0}_{1}_voice"\
            .format(self.user, str(self.current_turn).zfill(3))
        self.record_log(sys_utt)
        print("system:{}".format(sys_utt))
        sys_start_time = time.time() - self.base_time
        self.mmd.say(sys_utt)
        self.record_log("*")
        self.record.start(file_name)
        self.asr.start()
        while True:
            if self.asr.m_turn.is_sys_turn_end == True:
                break
            else:
                time.sleep(0.1)
        self.record.stop()
        user_turn_end = time.time() - self.base_time
        user_utt = self.asr.read_result()
        self.env.user_utterance_log.append(user_utt)
        user_start_time = self.asr.get_utt_start_time()
        # 録音したwavファイルが保存されるまで待機
        while True:
            if self.record.save_complete == True:
                time.sleep(0.1)
                break
            else:
                time.sleep(0.1)
        self.opensmile.run(file_name)
        print("user:{}".format(user_utt))

        # predict mono modal
        d_pred = self.predict_dialogue(user_utt, sys_utt, da, user_start_time)
        v_pred = self.predict_voice("{}.csv".format(file_name))
        t_pred = self.predict_text(user_utt)
        f_pred = self.predict_face(sys_start_time, user_turn_end)
        self.print_debug("dialogue predict:{}".format(d_pred))
        self.print_debug("voice predict:{}".format(v_pred))
        self.print_debug("text predict:{}".format(t_pred))
        self.print_debug("face predict:{}".format(f_pred))

        # fusion 4 modal
        df = pd.DataFrame(data=[[d_pred, v_pred, t_pred, f_pred]])
        X_test = df.iloc[0, :].values
        self.user_impression = pf.predUnknown(X_test, "fusion")
        # 値のrange変更
        self.user_impression = pf.changePredValueRange(self.user_impression)
        self.print_debug("user_impression:{}".format(self.user_impression))
        
        # 状態更新
        n_state = self.env.get_next_state(self.user_impression, sys_utt, user_utt)
        self.state = n_state

        # 終了判定
        self.current_turn += 1
        if self.current_turn == self.turn_num:
            is_end = True
        else:
            is_end = False
        return is_end
        

    def process_text(self):
        chg_theme, theme = self.themeHis.decideNextTheme(self.user_impression)
        # システム発話生成
        sys_utt, da = self.env.utterance_selection_softmax(\
            chg_theme, theme, self.agent.Q[self.state])
        # 発話選択
        self.env.sys_utterance_log.append(sys_utt)
        self.record_log(sys_utt)
        print("system:{}".format(sys_utt))
        self.record_log("*")
        user_utt = input("ユーザ発話>>")
        self.env.user_utterance_log.append(user_utt)
        print("user:{}".format(user_utt))

        self.user_impression = float(input("User impression>>"))
        # 状態更新
        n_state = self.env.get_next_state(self.user_impression, sys_utt, user_utt)
        self.state = n_state

        # 終了判定
        self.current_turn += 1
        if self.current_turn == self.turn_num:
            is_end = True
        else:
            is_end = False
        return is_end

    def predict_dialogue(self, user_utt, sys_utt, da, user_start_time):
        s_len = len(sys_utt)
        u_len = len(user_utt)
        diff = s_len - u_len
        df = pf.makeDiaDF(user_start_time, s_len, u_len, diff, da)
        X_test = df.iloc[0, :].values
        d_pred = pf.predUnknown(X_test, "dialogue")
        return d_pred

    def predict_voice(self, file_name):
        df = pd.read_csv(file_name)
        df = pf.selectVoiceFea(df, case="pred")
        X_test = df.iloc[0, :].values
        v_pred = pf.predUnknown(X_test, "voice")
        return v_pred

    def predict_text(self, user_utt):
        df = etf.makeFea(user_utt)
        pca = pickle.load(open("../refData/RL_files/modelUIpred/pca.model", "rb"))
        df = pf.PCAonlyBOW(df, pca=pca)
        X_test = df.iloc[0, 1:-1].values
        X_test = X_test.astype(np.float32)
        t_pred = pf.predUnknown(X_test, "text")
        return t_pred

    def predict_face(self, start, end):
        file_name = "{}/{}_face.csv".format(self.data_path, self.user)
        X_test = eff.predictionFace(start, end, file_name)
        f_pred = pf.predUnknown(X_test, "face")
        return f_pred

    def record_log(self, utt):
        """
        ログに発話を追加する．
        フォーマットはHazumiのログの仕様通り
        Parameters
        ----------
        utt : str
            ユーザ発話はすべて*として記録される
        """
        def format_time():
            t = datetime.datetime.now()
            s = t.strftime("%Y-%m-%dT%H:%M:%S.%f")
            tail = s[-7:]
            f = round(float(tail), 3)
            temp = "%.3f" % f
            return "%s%s" % (s[:-7], temp[1:])
        elapsed = round(time.time() - self.base_time, 3)
        self.log.append("{}, {}, {}".format(format_time(), elapsed, utt))

    def save_log(self):
        """
        記録したログをcsvファイルに出力する．
        対話設定を別のcsvファイルに出力する．
        ログのみ文字コードをutf-8としている．
        対話設定ファイルはshift-jis．
        ほかのcsv,txtファイルも全てshift-jis．
        """
        fp_log = "{}/{}.csv".format(self.data_path, self.user)
        fp_setting = "{}/{}_setting.csv".format(self.data_path, self.user)
        with open(fp_log, "w", encoding="utf-8") as f:
            w = csv.writer(f)
            for l in self.log:
                w.writerow(l)
        
        with open(fp_setting, "w", encoding="shift-jis") as f:
            w = csv.writer(f)
            w.writerow(["user", self.user])
            w.writerow(["model", self.model])
            w.writerow(["turn num", self.turn_num])
            if self.text == False:
                w.writerow(["ASR module", self.asr_module])
                w.writerow(["mode", self.mode])
                w.writerow(["response_time_no_word", self.asr.m_turn.response_time_no_word])
                w.writerow(["turn_buffer", self.asr.m_turn.turn_buffer])
                
def nh_test_offline():
    nh = NHChat(mode="WebCamera", asr_module="julius", is_debug=True)
    nh.run()
    
def nh_test_online():
    nh = NHChat(mode="online", asr_module="google", is_debug=True)
    nh.run()

def main():
    # options
    # コマンドエラー時に表示する文字列
    desc = u"{0} [Args] [Options]\nDetailed options -h or --help".format(__file__)
    
    parser = ArgumentParser(description=desc)
    parser.add_argument(
        "--model",
        type = str,
        dest = "model",
        default = "200117_c099",
        help = "強化学習モデル名(default:200117_c099)"
    )
    parser.add_argument(
        "--mode",
        type = str,
        dest = "mode",
        default = "WebCamera",
        help = "実行モード．onlineかWebCamera(default:WebCamera)"
    )
    parser.add_argument(
        "-u", "--user",
        type = str,
        dest = "user",
        default = "tmp_user",
        help = "ユーザ名(default:tmp_user)"
    )
    parser.add_argument(
        "--turn_num",
        type = int,
        dest = "turn_num",
        default = 3,
        help = "ターン数(default:3)"
    )
    parser.add_argument(
        "--text",
        type = bool,
        dest = "text",
        default = False,
        help = "テキストで対話を行うか(default:False)"
    )
    parser.add_argument(
        "--asr", "--asr_module",
        type = str,
        dest = "asr_module",
        default = "google",
        help = "音声認識モジュール．googleかjulius(default:google)"
    )
    parser.add_argument(
        "--response_time_no_word",
        type = float,
        dest = "response_time_no_word",
        default = 6.0,
        help = "ユーザターン開始後ユーザが発話しない場合，\
            どの程度待ってターンテイキングを行うか(default:6.0)"
    )
    parser.add_argument(
        "--turn_buffer",
        type = float,
        dest = "turn_buffer",
        default = 6.0,
        help = "ユーザ発話の音声認識が確定した後，\
            どの程度待ってターンテイキングを行うか(default:1.5)"
    )
    parser.add_argument(
        "--is_debug", "--debug",
        type = bool,
        dest = "is_debug",
        default = False,
        help = "デバックモードで実行するか(default:False)"
    )
    
    args = parser.parse_args()
    
    # nh_test_offline()
    # nh_test_online()
    
    nh = NHChat(model=args.model, mode=args.mode, user=args.user,
                turn_num=args.turn_num, text=args.text, asr_module=args.asr_module,
                response_time_no_word=args.response_time_no_word,
                turn_buffer=args.turn_buffer, is_debug=args.is_debug)
    nh.run()
    
if __name__ == "__main__":
    main()