# -*-coding: utf-8 -*-
import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
import pickle

# 桁数指定
np.set_printoptions(precision=3)


def makeDiaDF(reaction, s_len, u_len, su_len, da):
    """
    dialogueの素性df作成
    """
    # da(one-hot)
    da_list = ['io', 'na', 'oa', 'op', 'pa', 'qw', 'qy', 'su']
    da_fea = np.eye(8)[da_list.index(da)] if da in da_list else np.zeros(8)

    fea = [reaction, s_len, u_len, su_len] + da_fea.tolist()
    df = pd.DataFrame(data=[fea],
                      columns=['reaction', 'lenS', 'lenU', 'lendiff', 'io', 'na', 'oa', 'op', 'pa', 'qw', 'qy', 'su'])
    return df


# X_testは1データ分の特徴量ベクトル
# 1次元でnumpy形式指定で．
def predUnknown(X_test, fea_type, is_print=False):
    # 変形
    X_test = np.array([X_test.tolist()])
    # スケーリングデータ，分類器を読込
    scale = np.load(
        '../refData/RL_files/modelUIpred/{}_scale.npy'.format(fea_type))
    model = pickle.load(
        open('../refData/RL_files/modelUIpred/{}.model'.format(fea_type), 'rb'))

    maxi = scale[0]
    mini = scale[1]
    X_test[0] = (X_test[0] - mini) / (maxi - mini)
    # 推定
    y_pred = model.predict(X_test)

    if is_print:
        print('{}の推定結果 : {}'.format(fea_type, y_pred))
    return y_pred[0]


def selectVoiceFea(df, case='train'):

    FEAdf = pd.read_csv('../refData/voice_fea26.txt', header=None)
    if case == 'train':
        voice_feature = ['name'] + FEAdf[0].values.tolist() + ['label']
    elif case == 'pred':
        voice_feature = FEAdf[0].values
    else:
        print('invalid input in func selectVoiceFea')
        exit(0)

    return df[voice_feature]


def PCAonlyBOW(df, pca_dim=5, pca=None):
    meta = df.columns.values
    index = df['name'].values
    Xdata = df.iloc[:, 1:-1].values
    label = df['label'].values

    word_num = len([x for x in meta if 'word#' in x])
    XdataBow = Xdata[:, :word_num]
    XdataOrg = Xdata[:, word_num:]

    if pca == None:
        pca = PCA(n_components=pca_dim, random_state=0)
        pca.fit(XdataBow)

    XdataBow = pca.transform(XdataBow)
    new_Xdata = np.hstack((XdataBow, XdataOrg))

    # メタ作成
    meta = ['name'] + ["t_fea#" + str(i+1).zfill(2)
                       for i in range(len(new_Xdata[0]))] + ["label"]
    new_arr = np.hstack(
        (np.array([index]).transpose(), new_Xdata, np.array([label]).transpose()))
    df = pd.DataFrame(data=new_arr, columns=meta)

    return df

def changePredValueRange(fusion_pred):
    """
    心象を線形変換します
    """
    lowUI_before = x1 = 4.4
    lowUI_after = y1 = 3
    highUI_before = x2 = 4.6
    highUI_after = y2 = 5

    fusion_pred_scaled = ((y2-y1)/(x2-x1)) * (fusion_pred - x1) + y1

    if fusion_pred_scaled < 1:
        fusion_pred_scaled = 1
    if fusion_pred_scaled > 7:
        fusion_pred_scaled = 7

    return fusion_pred_scaled


if __name__ == '__main__':

    # ここは関数の保持のみを行うコード
    print('it is the code has main function.')

    # 推定値のrangeの調整
    import predUI as pf
    d_pred, v_pred, t_pred, f_pred = 4.0, 4.0, 0.1, 0.1
    df = pd.DataFrame(data=[[d_pred, v_pred, t_pred, f_pred]])
    X_test = df.iloc[0, :].values
    user_impression = pf.predUnknown(X_test, 'fusion')
