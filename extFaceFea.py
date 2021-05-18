# -*-coding: utf-8 -*-
import sys
import pandas as pd
import numpy as np
import os
import subprocess
import time
import pickle

import predUI as pf


#### モジュールです

def predictionFace(start, end, file_name='sample'):

	# 範囲指定
	df = pd.read_csv("C:/Users/kaldi/Desktop/OpenFace_2.0.5_win_x64/processed/{}.csv".format(file_name))
	df = df[(start < df[' timestamp']) & (df[' timestamp'] < end)]
	df_meta = pd.read_csv('./refData/actionunit.txt', header=None)
	meta = df_meta[0].values
	df = df[meta]
	# 特徴量設計（平均をとる）
	arrX = df.iloc[:, :].values
	face_features = np.average(arrX, axis=0)
	return face_features


if __name__ == '__main__':

	pass