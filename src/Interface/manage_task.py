# -*- coding:utf-8 -*-
import subprocess


class ManageTask:

    def __init__(self):
        pass

    def kill_task(self, task_name: str, is_print=False):
        """
        指定された名前のタスクが起動している場合タスクキルで終了

        Parameters
        ----------
        task_name : str
            キルするタスクの名前．
        is_print : bool, optional
            キルしたログを表示するかを制御する．
            デフォルトは表示しない．
        """
        pid_list, name_list = self.get_pid(task_name)
        for pid, name in zip(pid_list, name_list):
            cmd = "taskkill /F /pid {} > nul".format(pid)
            subprocess.call(cmd, shell=True)
            if is_print == True:
                print("kill {}({})".format(name, pid))

    def get_pid(self, task_name: str):
        """
        タスクの名前から該当するタスクの名前とプロセスIDを取得しリストで返す

        Parameters
        ----------
        task_name : str
            プロセスIDを取得するタスクの名前

        Returns
        -------
        pid_list : list
            プロセスIDのリスト
        name_list : list
            プロセス名のリスト

        """
        pid_list = []
        name_list = []
        # タスク一覧を取得
        proc = subprocess.Popen("tasklist", shell=True, stdout=subprocess.PIPE)
        for line in proc.stdout:
            line = line.decode(encoding='shift_jis')
            if task_name in line:
                pid_list.append(line.split()[1])
                name_list.append(line.split()[0])
        return pid_list, name_list

    def confirm_task(self, task_name: str, is_print=False):
        """
        指定したタスク名が実行中か確認する．
        実行中であればプロセスIDとともにプリントする．

        Parameters
        ----------
        task_name : str
            確認するタスクの名前
        is_print : bool
            プリントして表示するか
        Returns
        -------
        is_exist : bool
            task_nameに該当知るタスクが存在するか
        """
        is_exist = False
        pid_list, name_list = self.get_pid(task_name)
        for pid, name in zip(pid_list, name_list):
            if is_print == True:
                print("{}({})".format(name, pid))
            if task_name in name:
                is_exist = True
        return is_exist


def main():
    mt = ManageTask()
    task_name = input("検索するタスクの名前>>")
    mt.confirm_task(task_name)
    is_kill = input("タスクキルを行いますか？y/n>>")
    if is_kill == "y":
        mt.kill_task(task_name)


if __name__ == "__main__":
    main()
