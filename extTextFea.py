# -*-coding: utf-8 -*-

import re
import copy
import numpy as np
import sys
import os.path
import MeCab
import pandas as pd


##### MMシステム用に大幅に変更しています．######################

#search_wordがword_list（リスト）に存在するかを返す関数
def is_in_speech(word_list, search_word):
	for word in word_list:
		if search_word == word:
			return True
	return False
		

# 独自素性
# 文章から素性を抽出し，そのベクトルを返す．（素性数5）
def ext_origin(user_id, base_data, pos_data):
	# 素性の値:興味あり->1 興味なし->-1 不明->0
	text_features = []
	for line in base_data:
		text_features.append([])

	##fea1（無言なら興味ない）
	num = 0
	for line in base_data:
		if u'＊' in line:
			text_features[num].append(-1)
		else:
			text_features[num].append(0)
		num += 1

	##fea2-5（名詞，形容詞，副詞，感動詞の個数）
	num = 0
	for line in pos_data:
		text_features[num].append(line.count(u'名詞'))
		text_features[num].append(line.count(u'形容詞'))
		text_features[num].append(line.count(u'感動詞'))
		text_features[num].append(line.count(u'副詞'))
		num += 1

	return text_features

# bag−of−words（有無）
# 文章から素性を抽出し，そのベクトルを返す．
def ext_bow(user_id, base_data):
	# 付属語削除，使用回数制限
	df = pd.read_csv('./refData/1902wordList.txt', header=None)
	wordlist = df[1].values
	text_features = []
	# text_featuresの作成
	for line in base_data:
		line_data = []
		for word in wordlist:
			if is_in_speech(line, word):
				line_data.append(1)
			else:
				line_data.append(0)
		text_features.append(copy.deepcopy(line_data))

	return text_features

def makeTmeta():
	# road
	df = pd.read_csv('./refData/1902wordList.txt', header=None)
	wordlist = df[1].values
	bow = ['word#'] * len(wordlist)
	for i, val in enumerate(bow):
		bow[i] = bow[i] + str(i+1).zfill(3)
	origin = ['無言', '名詞', '形容詞', '感動詞', '副詞']
	meta = ['name'] + bow + origin + ['label']
	return meta


# 入力を1文としてfea抽出
def makeFea(input_text):
	m = MeCab.Tagger()
	morphs = m.parse(input_text)

	morphs = morphs.split('\n')
	for i, morph in enumerate(morphs):
		morphs[i] = morphs[i].split(',')

	pos_data, base_data = [], []
	pos, base = '', ''
	for i, val in enumerate(morphs):
		if val[0] != 'EOS':
			pos = pos + str(val[0].split('\t')[1]) + ' '
			base = base + str(val[6]) + ' '
		else:
			pos_data.append(pos)
			base_data.append(base)
			break

	bow_fea = ext_bow(0, base_data)
	org_fea = ext_origin(0, base_data, pos_data)

	# 未知のデータなので，nameとlabelはなんでもいい
	dammy = [['?']]
	text_features = np.hstack((dammy, bow_fea, org_fea, dammy))
	meta = makeTmeta()
	df = pd.DataFrame(data=text_features, columns=meta)
	return df



if __name__ == '__main__':

	print('this is code for ext text fea')



