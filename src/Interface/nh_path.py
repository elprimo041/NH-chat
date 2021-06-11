# -*- coding:utf-8 -*-
import csv
import pathlib
import os

class NHPath:
    """
    ../refData/path.csvを読み込み辞書として保持する
    """
    
    def __init__(self):
        self.path = {}
        with open("../refData/path.csv", encoding="shift-jis") as f:
            reader = csv.reader(f)
            for row in reader:
                self.path[row[0]] = row[1]

    def get_abs_path(self, name):
        """
        絶対パスを返す
        Parameters
        ----------
        name : str
            refData/path.csvの1列目の値(MMDAgentなど)

        Returns
        -------
        abs_path_slash : str
            絶対パス．
            階層の区切り文字をスラッシュに統一している．
        """
        p = pathlib.Path(self.path[name])
        abs_path = str(p.resolve())
        abs_path_slash = abs_path.replace(os.sep, "/")
        return abs_path_slash
    
    
def main():
    p = NHPath()
    print(p.path)
    print(p.get_abs_path("MMDAgent"))
    print(type(p.get_abs_path("MMDAgent")))
    
if __name__ == "__main__":
	main()