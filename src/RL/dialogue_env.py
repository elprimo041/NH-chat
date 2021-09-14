import MeCab
import copy
import pandas as pd
import numpy as np
import itertools
from sklearn import preprocessing
import re

from util import softmax
from params import Params


class DialogueEnv():
    """
    対話環境
    """

    def __init__(self):
        self.params = Params()
        self.history_sysutte = []
        self.history_sysutte_class = []

        # da
        self.da_df = pd.read_csv(self.params.get(
            'path_da_for_UIpred'), encoding="shift-jis")

        # action
        self.action_df = pd.read_csv(self.params.get(
            'path_class_name'), encoding="shift-jis")
        actions = self.action_df['clsname'].values.tolist()
        self.actions = actions

        # actionにindex付け
        self.actionIndex = {}
        for i, val in enumerate(self.actions):
            self.actionIndex[i] = val

        # 状態は「心象」「直前のシステム対話行為」「対話の位置」の組み合わせ
        self.states_sys_da = ['ct', 'io', 're', 'qs']
        self.states_noun_presence = ['Nx', 'No']
        self.states_impression = ['l', 'n', 'h']
        self.states = list(itertools.product(
            self.states_sys_da, self.states_noun_presence, self.states_impression))
        self.states = ['_'.join(x) for x in self.states]

        # stateにindex付け
        self.stateIndex = {}
        for i, val in enumerate(self.states):
            self.stateIndex[val] = i

        self.thres_low_UI = 3
        self.thres_high_UI = 5
        self.sys_utterance_log = []
        self.user_utterance_log = []
        self.weight_specific_theme = 0.6

    # システム発話の履歴を追加
    def add_sysutte(self, utterance, clas):
        self.history_sysutte.append(utterance)
        self.history_sysutte_class.append(clas)

    # 初期化のような感じ
    def reset(self):
        super().__init__()
        self.sys_utterance_log = []
        self.user_utterance_log = []
        return self.stateIndex['io_Nx_n']

    # 対話行為を簡単な分類に変換(4種類(ct/io/re/qs))
    def getSimpleDAFromSysUtterance(self, sys_utterance):
        df = pd.read_csv(self.params.get(
            'path_simple_da'), encoding="shift-jis")
        da = df[df['agent_utterance'] == sys_utterance]['da_simple'].values
        pattern = r"これから.+の話をしましょう"
        if re.search(pattern, sys_utterance) != None:
            simple_da = 'ct'
        else:
            simple_da = da[0]
        return simple_da

    # 心象を離散化
    def getImpressionLevel(self, impression):
        if impression <= self.thres_low_UI:
            impression_level = 'l'
        elif self.thres_high_UI <= impression:
            impression_level = 'h'
        else:
            impression_level = 'n'
        return impression_level

    # 文から固有名詞/一般名詞の存在有無を判断
    def getSpecificNoun(self, sentence):
        mt = MeCab.Tagger()
        node = mt.parseToNode(sentence)
        properNouns = []
        while node:
            fields = node.feature.split(",")
            if (fields[0] == '名詞') and (fields[1] in ['固有名詞', '一般']):
                properNouns.append(node.surface)
            node = node.next
        return 'No' if len(properNouns) > 0 else 'Nx'

    # 次のstateを決定
    def get_next_state(self, impression, sys_utterance, user_utterance):
        da_simple = self.getSimpleDAFromSysUtterance(sys_utterance)
        impression_level = self.getImpressionLevel(impression)
        noun_presence = self.getSpecificNoun(user_utterance)
        n_state = self.stateIndex['{}_{}_{}'.format(
            da_simple, noun_presence, impression_level)]
        return n_state

    # 特定話題の選択に重み（weight）をつける
    def weightSpecificTheme(self, df):
        themes = df['theme'].values
        themes = [1-self.weight_specific_theme if t ==
                  'default' else self.weight_specific_theme for t in themes]
        themes = [x/np.sum(themes) for x in themes]
        df = df.reset_index(drop=True)
        select_index = np.random.choice(df.index.values, p=themes)
        return df.loc[select_index]

    # actionに基づいた発話選択（ランダム選択）
    # heatmapにsoftmaxをちゃんと反映させた
    def utterance_selection_softmax(self, chg_theme, theme, prob_actions, mei_cmd=True):
        actions = copy.deepcopy(self.actions)
        prob_actions = copy.deepcopy(prob_actions)
        prob_actions = preprocessing.minmax_scale(prob_actions).tolist()  # 正規化

        # 話題変更のタイミングでは専用の発話を使用する
        if chg_theme:
            next_sysutte = 'これから{}の話をしましょう'.format(theme)
            self.add_sysutte(next_sysutte, 'change_theme')
        else:
            done = False
            while not done:
                # 選択する
                action = np.random.choice(
                    actions, p=softmax(prob_actions, coef=5))
                df = pd.read_csv(self.params.get(
                    'path_utterance_by_class_named'), encoding="shift-jis")
                CANDIDATEdf = df[(df['cls'] == action) &
                                 ((df['theme'] == theme) | (df['theme'] == 'default'))]
                CANDIDATEdf = CANDIDATEdf.reset_index(drop=True)
                CANDIDATEdf = CANDIDATEdf[['agent_utterance', 'theme', 'cls']]
                # 使えないものを削除
                for i in range(len(CANDIDATEdf)):
                    if CANDIDATEdf.loc[i, :]['agent_utterance'] in self.history_sysutte:
                        CANDIDATEdf = CANDIDATEdf.drop(index=[i])
                # 候補が残っていない
                if len(CANDIDATEdf) == 0:
                    index = np.where(np.array(actions) == action)[0]
                    actions.pop(index[0])
                    prob_actions.pop(index[0])
                # 候補が残っている（選択して終了）
                else:
                    SELECTdf = self.weightSpecificTheme(CANDIDATEdf)
                    next_sysutte, next_theme, next_action = SELECTdf.values
                    self.add_sysutte(next_sysutte, next_action)
                    done = True

        if mei_cmd:
            # print(next_sysutte)
            command = "SYNTH_START|mei|mei_voice_normal|" + next_sysutte
            command = command.encode("shift_jis")
            if chg_theme:
                return next_sysutte, 'op'
            else:
                da = self.da_df[self.da_df['speech'] ==
                                next_sysutte]['dialogue_act'].values[0]
                return next_sysutte, da
        else:
            return next_sysutte


if __name__ == '__main__':
    pass
