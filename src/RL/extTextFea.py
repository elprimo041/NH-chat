# -*-coding: utf-8 -*-
import numpy as np
import MeCab
import pandas as pd


##### MMシステム用に大幅に変更しています．######################

# 独自素性
# 文章から素性を抽出し，そのベクトルを返す．（素性数5）
def ext_origin(base_data, pos_data):
    text_features = [
        [
            # fea1（無言なら興味ない）# 素性の値:興味あり->1 興味なし->-1 不明->0
            -1 if u'＊' in base_line else 0,
            # fea2-5（名詞，形容詞，副詞，感動詞の個数）
            pos_line.count(u'名詞'),
            pos_line.count(u'形容詞'),
            pos_line.count(u'感動詞'),
            pos_line.count(u'副詞')
        ] for base_line, pos_line in zip(base_data, pos_data)
    ]
    return text_features

# bag−of−words（有無）
# 文章から素性を抽出し，そのベクトルを返す．


def ext_bow(base_data):
    # 付属語削除，使用回数制限
    df = pd.read_csv('../refData/1902wordList.txt',
                     header=None, encoding="shift-jis")
    wordlist = df[1].values

    # text_featuresの作成
    text_features = [
        [1 if word in line else 0 for word in wordlist] for line in base_data
    ]

    return text_features


def makeTmeta():
    # road
    df = pd.read_csv('../refData/1902wordList.txt',
                     header=None, encoding="shift-jis")
    wordlist = df[1].values
    bow = ['word#' + str(i+1).zfill(3) for i in range(len(wordlist))]
    origin = ['無言', '名詞', '形容詞', '感動詞', '副詞']
    meta = ['name'] + bow + origin + ['label']
    return meta


# 入力を1文としてfea抽出
def makeFea(input_text):
    m = MeCab.Tagger()
    morphs = m.parse(input_text)
    morphs = morphs.split('\n')
    morphs = [morph.split(',') for morph in morphs]

    pos_data, base_data = [], []
    pos, base = '', ''
    for val in morphs:
        if val[0] != 'EOS':
            pos = pos + str(val[0].split('\t')[1]) + ' '
            base = base + str(val[6]) + ' '
        else:
            pos_data.append(pos)
            base_data.append(base)
            break

    bow_fea = ext_bow(base_data)
    org_fea = ext_origin(base_data, pos_data)

    # 未知のデータなので，nameとlabelはなんでもいい
    dammy = [['?']]
    text_features = np.hstack((dammy, bow_fea, org_fea, dammy))
    meta = makeTmeta()
    df = pd.DataFrame(data=text_features, columns=meta)
    return df


if __name__ == '__main__':

    print('this is code for ext text fea')
