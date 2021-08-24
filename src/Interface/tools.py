# -*- coding:utf-8 -*-
import subprocess
import threading
import time
import sys
import os
import re
from socket import gethostname

from nh_path import NHPath
from manage_task import ManageTask
from abstract_communicator import AbstractCommunicator

CAMERA_NUM_OFFLINE = 0
CAMERA_NUM_ONLINE = 2

SAMPLE_RATE = 16000
CHUNK_SIZE = int(SAMPLE_RATE / 10)  # 100ms

class Record:
    """
    soxを用いて録音する．
    start時にファイル名を指定する．
    """

    def __init__(self, is_debug=False):
        self.is_recording = False
        self.save_complete = False
        self.debug = is_debug
        self.proc = None
        self.command_common = "sox -t waveaudio -d {}"

    def __del__(self):
        if self.is_recording == True:
            self.stop()

    def set_debug(self, debug):
        self.debug = debug

    def print_debug(self, message):
        if(self.debug):
            print(message)

    def start(self, file_name):
        if file_name.endswith(".wav") == False:
            file_name = file_name + ".wav"
        command = self.command_common.format(file_name)
        self.print_debug("start recording:{}".format(file_name))
        self.print_debug("sox command:\n{}".format(command))
        self.is_recording = True
        self.save_complete = False
        # Popen(command, shell=True)だと録音が正しく終了できない
        self.proc = subprocess.Popen(command.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        

    def stop(self):
        self.print_debug("end recording")
        self.proc.terminate()
        try:
            self.proc.wait(timeout=1)
        except subprocess.TimeoutExpired:
            self.proc.kill()
        self.is_recording = False
        self.save_complete = True


class OpenSmile:
    """
    音声から韻律情報を抽出しcsvに変換する．
    runに音声ファイルのパスを入れるとcsvが出力される．
    openSMILE3.0はpythonに対応しているが特徴量セットが未対応のためコマンドからの実行．
    特徴量セットに縛りがない場合はもっと簡単に実装できる．
    https://qiita.com/Nahuel/items/e8745bfbd710a90a7ca3
    """

    def __init__(self, is_debug=False):
        self.debug = is_debug
        # read path	
        nh_path = NHPath()
        try:
            smile_path = nh_path.path["openSMILE"]
        except KeyError:
            print("openSMILE path undefined")
            sys.exit()
        self.cmd_common = "{0}/bin/SMILExtract.exe \
            -C {0}/config/is09-13/IS09_emotion.conf"\
            .format(smile_path) + " -I {}.wav -O {}.arff"
        self.print_debug("smile common command:\n{}".format(self.cmd_common))

    def set_debug(self, debug):
        self.debug = debug

    def print_debug(self, message):
        if(self.debug):
            print(message)

    def run(self, file_name):
        # .wavを外す
        if file_name.endswith(".wav"):
            file_name = file_name[:-4]
        # 同名のarffとcsvがある場合は削除
        if os.path.isfile("{}.arff".format(file_name)):
            os.remove("{}.arff".format(file_name))
            self.print_debug("delete {}.arff".format(file_name))
        if os.path.isfile("{}.csv".format(file_name)): 
            os.remove("{}.csv".format(file_name))
            self.print_debug("delete {}.csv".format(file_name))
            
        cmd = self.cmd_common.format(file_name, file_name)
        self.print_debug("command openSMILE:\n{}".format(cmd))
        subprocess.call(cmd.split(" "), shell=True, stdout=subprocess.PIPE, \
            stderr=subprocess.PIPE)
        # arffが作成されるまで待機
        while True:
            if os.path.isfile("{}.arff".format(file_name)):
                time.sleep(0.1)
                break
        with open("{}.arff".format(file_name) , "r") as f_in:
            content = f_in.readlines()
            new = self.arff_to_csv(content)
        with open("{}.csv".format(file_name), "w", encoding="shift-jis") as f_out:
            f_out.writelines(new)

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
                if line != "\n":
                    newContent.append(line)
        return newContent


class OpenFace:
    """
    OpenFaceのFeatureExtraction.exeを用いて顔画像のアクションユニットを抽出する．
    Webカメラの設定方法は開発者向け仕様書.pdfを参照．
    """

    def __init__(self, mode="WebCamera", is_debug=False):
        self.debug = is_debug
        # read path	
        nh_path = NHPath()
        try:
            face_path = nh_path.path["OpenFace"]
        except KeyError:
            print("OpenFace path undefined")
            sys.exit()
        # init
        self.mode = mode
        if self.mode not in ["WebCamera", "online"]:
            raise Exception("OpenFace mode is incorrect:{}".format(self.mode))
        self.is_running = False
        self.proc = None
        self.m_task = ManageTask()
        
        # init command
        if self.mode == "WebCamera":
            self.cmd_common = "{}/FeatureExtraction.exe -device {} -aus -of "\
                .format(face_path, CAMERA_NUM_OFFLINE)
        elif self.mode == "online":
            self.cmd_common = "{}/FeatureExtraction.exe -cam_width 960\
                -cam_height 540 -device {} -aus -of "\
                .format(face_path, CAMERA_NUM_ONLINE)        

    def set_debug(self, debug):
        self.debug = debug

    def print_debug(self, message):
        if(self.debug):
            print(message)

    def start(self, file_name):
        def start_thread(self, file_name):
            if self.is_running == True:
                print("openface is alrady running")
                return
            if not file_name.endswith(".csv"):
                file_name += ".csv"
            cmd = self.cmd_common + file_name
            self.print_debug("OpenFace command:\n{}".format(cmd))
            self.proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,\
                stderr=subprocess.PIPE)
            activate_time = time.time()
            print('#### OpenFace:Initiating start ####')
            while True:
                elapsed = time.time() - activate_time
                if elapsed > 15:
                    raise TimeoutError("OpenFaceの起動に失敗しました")
                line = self.proc.stdout.readline().decode()
                if line != "":
                    self.print_debug(line)
                if "Starting tracking" in line:
                    print('#### OpenFace:Initiating Done ####')
                    break
            self.is_running = True
        thread = threading.Thread(target=start_thread, args=(self, file_name,))
        thread.start()

    def stop(self):
        if self.is_running == False:
            print("OpenFace is not running")
            return
        self.print_debug("stop OpenFace")
        self.is_running = False
        self.proc.kill()
        self.m_task.kill_task("FeatureExtraction.exe")


class MMDAgent(AbstractCommunicator):
    """
    MMDAgentを起動し，発話や動作の実行を行う．
    """

    def __init__(self, is_activate_confirm=True ,is_debug=False):
        self.debug = is_debug
        host = "%s" % gethostname()
        port = 39390
        
        # すでにMMDAgentが実行中の場合はキル
        self.m_task = ManageTask()
        if self.m_task.confirm_task("MMDAgent-EX") == True:
            self.m_task.kill_task("MMDAgent-EX")
            time.sleep(1)
        super(MMDAgent, self).__init__(host, port)
        
        # read path	
        nh_path = NHPath()
        try:
            mmd_exe_path = nh_path.path["MMDAgent-EX"]
            self.mmd_example_path = nh_path.path["MMDExample"]
        except KeyError:
            print("MMDAgent or MMDExample path undefined")
            sys.exit()
        cmd = "{}/MMDAgent-EX.exe {}/MMDAgent_Example.mdf"\
            .format(mmd_exe_path, self.mmd_example_path)
        
        # run MMDAgent
        self.print_debug("command MMD:\n{}".format(cmd))
        self.proc = subprocess.Popen(cmd, shell=True)
        
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
        self.print_debug("connect to MMDAgent")
        time.sleep(3)
        self.is_speaking = False
        self.base_time = time.time()
        
        if is_activate_confirm == True:
            self.say("MMDAgentを起動しました")

        self.speak_start_command_time = None
        self.speak_end_command_time = None

    def __del__(self):
        self.end()

    def set_debug(self, debug):
        self.debug = debug

    def print_debug(self, message):
        if self.debug:
            print(message)
            
    def say(self, speech):
        # speechが長すぎると強制終了するので分割
        # 恐らくlen(speech) > 90でエラー？
        # MMDAgentは文末文字(？．。！など)によって発音が変わらないみたいなので
        # 文末文字を含めずに分割しています
        speech_list = re.split("[。．!！?？]", speech)
        # リストから空白要素""を削除
        speech_list = [utt for utt in speech_list if utt != ""]
        self.print_debug(speech_list)
        for s in speech_list:
            if len(s) > 90:
                # 分割後しても長ければスキップ
                print("発話が長すぎます．一度の発話を90文字以内にしてください．")
                print(speech)
                continue
            command =  'SYNTH_START|mei|mei_voice_normal|{}'.format(s)
            self.print_debug("command:\n{}".format(command))
            self.is_speaking = True
            speak_start = time.time()
            limit = 5 + len(speech) / 2.5
            self.send_line(command, "utf-8")
            while self.is_speaking:
                elapsed = time.time() - speak_start
                if elapsed > limit:
                    print("speak_start:{}".format(speak_start))
                    print("elapsed:{}".format(elapsed))
                    print("limit:{}".format(limit))
                    raise TimeoutError("音声合成でタイムアウトが発生しました")
                else:
                    time.sleep(0.1)
            
            

    def move(self, motion):
        fp = "{0}/Motion/{1}/{1}.vmd".format(self.mmd_example_path, motion)
        if os.path.isfile(fp):
            command = "MOTION_ADD|mei|action|" + fp + "|PART|ONCE"
            self.print_debug("command:\n{}".format(command))
            self.send_line(command, "shift_jis")
        else:
            print("motion command is not found:{}".format(motion))

    def express(self, expression):
        fp = "{0}/Expression/{1}/{1}.vmd".format(self.mmd_example_path, expression)
        if os.path.isfile(fp):
            command = "MOTION_ADD|mei|action|" + fp + "|PART|ONCE"
            self.print_debug("command:\n{}".format(command))
            self.send_line(command, "shift_jis")
        else:
            print("expression file is not found:{}".format(expression))

    def on_received(self, message):
        # self.print_debug("====================================")
        # self.print_debug(message)
        # self.print_debug("====================================")
        if "RECOG_EVENT_START" in message:
            self.print_debug("音声認識開始")
        elif "RECOG_EVENT_STOP" in message:
            self.print_debug("音声認識終了")
        elif "SYNTH_EVENT_START" in message:
            self.print_debug("音声合成開始")
            self.speak_start_command_time = time.time()
        elif "SYNTH_EVENT_STOP" in message:
            self.print_debug("音声合成終了")
            self.speak_end_command_time = time.time()
            self.is_speaking = False
        elif "LIPSYNC_EVENT_START" in message:
            self.print_debug("唇開始")
        elif "LIPSYNC_EVENT_STOP" in message:
            self.print_debug("唇終了")
        elif "MOTION_EVENT_ADD" in message:
        	self.print_debug("動作開始")
        elif "MOTION_EVENT_CHANGE" in message:
        	self.print_debug("動作変更")
        elif "MOTION_EVENT_DELETE" in message:
        	self.print_debug("動作終了")
        

    def end(self):
        self.stop()
        self.proc.terminate()
        self.m_task.kill_task("MMDAgent")


def record_test():
    rec = Record(is_debug=True)
    print("5秒間の録音を行います")
    f_name = input("input record file name>>")
    rec.start(f_name)
    print("録音中...")
    time.sleep(5)
    rec.stop()

def smile_test(fp):
    smile = OpenSmile(is_debug=True)
    smile.run(fp)

def face_test():
    face = OpenFace(is_debug=True)
    face.start("tmp/tmp.csv")
    time.sleep(15)
    face.stop()
    
def mmd_test():
    mmd = MMDAgent(is_debug=True)
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
    
def main():
    # record_test()
    # smile_test("tmp.wav")
    # face_test()
    mmd_test()
    
if __name__ == "__main__":
    main()