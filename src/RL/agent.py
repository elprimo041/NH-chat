import pickle

from params import Params


class TrainedQlearningAgent(Params):
    def __init__(self, filename):
        super().__init__()
        self.Q = {}

        # 学習すみQテーブルの読み込み
        with open(filename, mode='rb') as f:
            self.Q = pickle.load(f)

    # Qの学習されていないところを埋める
    def fillQ(self, env):
        for k in range(len(env.states)):
            if k not in self.Q.keys():
                self.Q[k] = [0] * len(env.actions)
