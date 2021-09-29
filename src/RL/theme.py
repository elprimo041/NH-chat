# -*- coding:utf-8 -*-
import numpy as np
import pandas as pd

from params import Params


# themeを管理してます
class HistoryTheme(Params):
    def __init__(self, random_choice=True):
        super().__init__()
        self.allTheme = list(pd.read_csv(self.get('path_using_theme'),
                                         header=None, encoding="shift-jis")[0].values)
        self.random_choice = random_choice
        self.nowTheme_ExchgNum = 0
        self.history_impression_1theme = []
        self.max_exchange_num_1theme = 10
        self.min_exchange_num_1theme = 5
        self.low_UI3_border = 3

    # 最初，話題変更する時はUIにNoneを入れること
    def decideNextTheme(self, UI):
        # 変更可否の決定
        if UI == None:
            chg = True
        elif self.nowTheme_ExchgNum >= self.max_exchange_num_1theme-1:
            chg = True
        elif (self.nowTheme_ExchgNum >= self.min_exchange_num_1theme-1) and \
                (np.mean(self.history_impression_1theme) < self.low_UI3_border):
            chg = True
        else:
            chg = False

        if chg:  # 変更
            if self.random_choice:
                self.nowTheme = np.random.choice(self.allTheme)
            else:
                print('使用する話題をindexで指定してください')
                for i, val in enumerate(self.allTheme):
                    print(i, val)
                index = int(input('>> '))
                self.nowTheme = self.allTheme[index]
            self.allTheme.remove(self.nowTheme)
            self.nowTheme_ExchgNum = 0
            self.history_impression_1theme = []
        else:  # 変更しない
            self.nowTheme_ExchgNum += 1
            self.history_impression_1theme.append(UI)

        return chg, self.nowTheme
