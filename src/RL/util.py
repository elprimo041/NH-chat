import numpy as np



def softmax(array, coef=1):
    """
    ソフトマックス関数

    Parameters
    ----------
    coef : int
        推定値の振れ幅を調整するためのもの．（デフォルトは1）
    """
    # 各要素から一番大きな値を引く（オーバーフロー対策）
    exp_a = np.exp(coef * (array - np.max(array)))
    sum_exp_a = np.sum(exp_a)
    # 要素の値/全体の要素の合計
    y = exp_a / sum_exp_a
    return y
