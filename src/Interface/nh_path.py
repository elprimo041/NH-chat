# -*- coding:utf-8 -*-
import csv
import pathlib
import os

class NHPath:
    """
    ../refData/path.csvを読み込み辞書として保持する
    """
    
    def __init__(self, is_debug=False):
        self.debug = is_debug
        fp = os.path.join(os.path.dirname(__file__), "../refData/path.csv")
        fp = fp.replace(os.sep, "/")
        self.print_debug("read:{}".format(fp))
        self.path = {}
        with open(fp, encoding="shift-jis") as f:
            reader = csv.reader(f)
            for row in reader:
                path_tmp = row[1]
                abs_path = os.path.join(os.path.dirname(__file__), path_tmp)
                abs_path = abs_path.replace(os.sep, "/")
                self.path[row[0]] = abs_path
                self.print_debug("{}:{}".format(row[0], abs_path))

    def set_debug(self, debug):
        self.debug = debug

    def print_debug(self, message):
        if(self.debug):
            print(message)
    
def main():
    p = NHPath()
    print(p.path)
    print(p.get_abs_path("MMDAgent"))
    print(type(p.get_abs_path("MMDAgent")))
    
if __name__ == "__main__":
	main()