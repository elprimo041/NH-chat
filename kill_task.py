# -*- coding:utf-8 -*-
import subprocess

def kill_task(task_name, is_print=False):
	# 指定された名前のタスクが起動している場合タスクキルで終了
	proc = subprocess.Popen("tasklist", shell=True, stdout=subprocess.PIPE)
	for line in proc.stdout:
		line = line.decode(encoding='shift_jis')
		if task_name in line:
			pid = line.split()[1]
			if is_print == True:
				cmd = "taskkill /F /pid {}".format(pid)
			else:
				cmd = "taskkill /F /pid {} > nul".format(pid)
			_ = subprocess.call(cmd, shell=True)