# -*-coding: utf-8 -*-
import numpy as np
from sklearn import svm
import pandas as pd
from sklearn.decomposition import PCA
from sklearn import preprocessing
import pickle

import predUI as pf

# 分類器作成
def makeModel(df, clf, filepath):
	X_train = df.iloc[:, 1:-1].values
	y_train = df['label'].values

	# 説明変数を取り出した上でスケーリング
	X_train = preprocessing.minmax_scale(X_train)
	# 分類器の構築
	clf.fit(X_train, y_train)
	# save
	pickle.dump(clf, open(filepath, 'wb'))

# textPCA(bow)のモデル作成
def makePCAModel(df, filepath, pca_dim=4):
	meta = df.columns.values
	Xdata = df.iloc[:, 1:-1].values

	word_num = len([x for x in meta if 'word#' in x])
	XdataBow = Xdata[:, :word_num]
	XdataOrg = Xdata[:, word_num:]

	pca = PCA(n_components=pca_dim, random_state=0)
	pca.fit(XdataBow)
	pickle.dump(pca, open(filepath, 'wb'))


# 特徴量スケーリングのmaxminの書き出し
def scaling(arrX, filepath):
	maxi = arrX.max(axis=0).tolist()
	mini = arrX.min(axis=0).tolist()
	# すべての特徴量が同じ値だった時の処理
	for i, (e_max, e_min) in enumerate(zip(maxi, mini)):
		if e_max == e_min:
			maxi[i], mini[i] = 1, 0

	max_min = np.array([maxi, mini])
	np.save(filepath, max_min)
	return 0

# dfから不適切な行を削除（列'label'の'E'や' 'を排除）
def remDataFrameError(df, meta='label', remove=True, devision=True):
	df[meta] = df[meta].astype('str')
	df[meta] = df[meta].replace(r'\D', '', regex=True)
	if remove == True:
		df = df[df[meta] != '']
		df[meta] = df[meta].astype('int')
	if devision == True:
		df[meta] = df[meta].values /10.0
	return df


if __name__ == '__main__':

	print('作成したいmodel	の種類を選択してください．')
	print('dialogue/voice/text/face//fusion/pca')
	fea_type = input('>>>  ')

	if fea_type == 'pca':
		df = pd.read_csv('./UIdata/text.csv')
		df = remDataFrameError(df)
		makePCAModel(df, './modelUIpred/pca.model', pca_dim=4)
	else:
		# 読込
		df = pd.read_csv('./UIdata/{}.csv'.format(fea_type))
		df = remDataFrameError(df)

		# 特徴量の前処理
		if fea_type == 'voice':
			df = pf.selectVoiceFea(df, case='train')
		if fea_type == 'text':
			df = pf.PCAonlyBOW(df, pca_dim=4)
		if fea_type == 'fusion':
			df = df.iloc[:, :-1]

		# 分類器の指定
		if fea_type == 'face':
			clf = svm.SVR(kernel='rbf', gamma='auto', C=0.1)
		else:
			clf = svm.SVR(kernel='rbf', gamma='auto', C=0.01)

		# 分類器の作成
		makeModel(df, clf, '../refData/RL_files/modelUIpred/{}.model'.format(fea_type))
		# maxminのスケーリングの作成
		scaling(df.iloc[:, 1:-1], '../refData/RL_files/modelUIpred/{}_scale.npy'.format(fea_type))

