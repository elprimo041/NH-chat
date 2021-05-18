# -*- coding:utf-8 -*-
import numpy as np
import pandas as pd


# パラメータ持ちです
class params:
	def __init__(self):
		self.params = {}
		self.param_file_name = './refData/parameters.txt'

		with open(self.param_file_name, 'r', encoding="utf-8")as f:
			paramInfo = f.readlines()
		paramInfo = [x.replace('\n', '') for x in paramInfo]
		paramInfo = [x for x in paramInfo if x != '']
		paramInfo = [x for x in paramInfo if '#' not in x]
		paramInfo = [x.split('=') for x in paramInfo]
		for i, val in enumerate(paramInfo):
			self.params[paramInfo[i][0]] = paramInfo[i][1]

	def get(self, param_name, system_action_type=''):

		if (param_name == 'priprob_UI3') or (param_name == 'STP_UI3'):
			# クラス名を読み込み，それを数字に変換
			ACTindex = {}
			df = pd.read_csv(self.params['path_main_class_info'])
			act = sorted(list(set(df['cls'].values)))
			for i, val in enumerate(act):
				ACTindex[val] = i

		if param_name == 'priprob_UI3':
			priprob = np.load(self.params['path_priprob'])
			priprob = priprob[:, ACTindex[system_action_type]]
			for i, val in enumerate(priprob):
				ratio = lambda x:x/sum(x)
				if int(val) == 0:
					priprob[i] = 1	# 要素が0なら1で埋める
			return ratio(priprob)
		elif param_name == 'STP_UI3':
			STPall = np.load(self.params['path_STP'])
			STP = STPall[:, :, ACTindex[system_action_type]]
			STP = np.where(STP == 0, 1, STP)	# 要素が0なら1で埋める
			return STP
		else:
			return self.params[param_name]



