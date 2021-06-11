import numpy as np
import matplotlib.pyplot as plt
import sys
import pandas as pd
import pickle
import os
import itertools
from sklearn import preprocessing
from collections import defaultdict

from theme import HistoryTheme
from params import Params



class Agent(Params):
    def __init__(self, epsilon):
        super().__init__()
        self.Q = {}
        self.epsilon = epsilon
        self.reward_log = []
        self.dialogue_log = []
        self.max_n_exchg = 10

    # epsilon以下でランダムな行動，それ以外はQに従った行動
    # softmax=Trueで確率的に選択するようにできます
    def policy(self, s, actions, selection='argmax'):

        if selection == 'argmax':
            if np.random.random() < self.epsilon:
                return np.random.randint(len(actions))
            else:
                if s in self.Q and sum(self.Q[s]) != 0:
                    return np.argmax(self.Q[s])
                else:
                    return np.random.randint(len(actions))
        elif selection == 'softmax':
            if np.random.random() < self.epsilon:
                return np.random.randint(len(actions))
            else:
                if s in self.Q and sum(self.Q[s]) != 0:
                    return np.argmax(self.softmax(preprocessing.minmax_scale(self.Q[s])))
                else:
                    return np.random.randint(len(actions))
        else:
            print('invalid "selection"')
            exit(0)


    def init_log(self):
        self.reward_log = []
        self.dialogue_log = []

    def append_log_reward(self, reward):
        self.reward_log.append(reward)

    def append_log_dialogue(self, exchgID, state, action, theme, impression, s_utte, u_utte):
        self.dialogue_log.append([exchgID+'_S', state, action, theme, '-', s_utte])
        self.dialogue_log.append([exchgID+'_U', '-', '-', '-', impression, u_utte])

    def show_reward_log(self, interval=50, episode=-1, filename='sample.png'):
        if episode > 0:
            rewards = self.reward_log[-interval:]
            mean = np.round(np.mean(rewards), 3)
            std = np.round(np.std(rewards), 3)
            print("At Episode {} average reward is {} (+/-{}).".format(
                   episode, mean, std))
        else:
            indices = list(range(0, len(self.reward_log), interval))
            means = []
            stds = []
            for i in indices:
                rewards = self.reward_log[i:(i + interval)]
                means.append(np.mean(rewards))
                stds.append(np.std(rewards))
            means = np.array(means)
            stds = np.array(stds)
            plt.figure()
            plt.title("Reward History")
            plt.grid()
            plt.fill_between(indices, means - stds, means + stds,
                             alpha=0.1, color="g")
            plt.plot(indices, means, "o-", color="g",
                     label="Rewards for each {} episode".format(interval))
            plt.legend(loc="best")
            plt.savefig(filename)
            #plt.show()

    def write_dialogue_log(self, filename):

        # ファイルが既に存在する場合，代わりの名前を振ってあげる．
        def search_and_rename_filename(oldpath):
            if os.path.exists(oldpath):
                print('file "{}" already exists.'.format(oldpath))
                #dirpath:ディレクトリのパス, filename:対象のファイルまたはディレクトリ
                #name:対象のファイルまたはディレクトリ（拡張子なし）, ext:拡張子
                dirpath, filename = os.path.split(oldpath)
                name, ext = os.path.splitext(filename)

                for i in itertools.count(1):
                    newname = '{}_{}{}'.format(name, i, ext)
                    newpath = os.path.join(dirpath, newname)
                    if not os.path.exists(newpath):
                        return newpath
                    else:
                        print('file "{}" already exists.'.format(newpath))
            else:
                return oldpath

                
        df = pd.DataFrame(data=self.dialogue_log, columns=['exchgID', 'state', 'action', 'theme', 'UI', 'utterance'])
        filename_new = search_and_rename_filename(filename)
        df.to_csv(filename_new, index=None)
        print('finished making file "{}".'.format(filename_new))




    def saveR(self, filename):
        np.save(filename, np.array(self.reward_log))

    def saveQ(self, table, filename):
        with open(filename, mode='wb') as f:
            pickle.dump(dict(table), f)


    # ソフトマックス関数
    # coefは推定値の振れ幅を調整するためのもの．（デフォルトは1）
    def softmax(self, a, coef=1):
        c = np.max(a)
        exp_a = np.exp(coef * (a - c))
        sum_exp_a = np.sum(exp_a)
        y = exp_a / sum_exp_a
        return y







# システム側（学習済み）
class TrainedQlearningAgent(Agent):
    def __init__(self, filename):
        super().__init__(epsilon=0)

        # 学習すみQテーブルの読み込み
        with open(filename, mode='rb') as f:
            self.Q = pickle.load(f)

    # Qの学習されていないところを埋める
    def fillQ(self, env):
        for k in range(len(env.states)):
            if k not in self.Q.keys():
                self.Q[k] = [0] * len(env.actions)
            else:
                pass

    # システム発話を入力として，(class, theme)を出力する
    def getUtteranceClassTheme(self, utterance):
        classFile = self.get('path_utterance_by_class_named')
        themeFile = self.get('path_theme_info')
        CLSdf = pd.read_csv(classFile)
        THEMEdf = pd.read_csv(themeFile)

        if '***' in utterance:
            return '-', '-'
        else:
            clsInfo = CLSdf[CLSdf['agent_utterance'] == utterance]['cls'].values.astype('str')
            clsInfo = '-'.join(clsInfo)
            themeInfo = THEMEdf[THEMEdf['agent_utterance'] == utterance]['theme'].values[0]
            return clsInfo, themeInfo

    def conversation(self, env):
        self.init_log()
        actions = list(env.actionIndex.keys())

        s = env.reset()#reset
        themeHis = HistoryTheme(random_choice=False)#reset
        for n_exchg in range(self.max_n_exchg):
            if n_exchg == 0:
                chg_theme, theme = themeHis.decideNextTheme(None)
            else:
                chg_theme, theme = themeHis.decideNextTheme(impression)

            sys_utterance = env.utterance_selection_softmax(chg_theme, theme, self.Q[s], coef=5)# 発話選択
            print(sys_utterance)
            user_utterance = input('your utterance >> ')# 発話入力
            impression = float(input('your impression >> '))# 心象入力
            n_state = env.get_next_state(impression, sys_utterance, user_utterance)

            states = [k for k, v in env.stateIndex.items() if v == s]
            self.append_log_dialogue(str(n_exchg).zfill(2),
                states[0],
                env.history_sysutte_class[-1],
                self.getUtteranceClassTheme(sys_utterance)[1],
                impression,
                sys_utterance,
                user_utterance)

            # 更新
            s = n_state





