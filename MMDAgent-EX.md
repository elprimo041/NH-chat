# MMDAgent-EX への更新手順

## 前提


すでに MMDAgent_Example-1.4 をダウンロード済みであり、MMDAgent を利用して NH-chat が実行できる状態になっている

## MMDAgent-EX のダウンロード

1. [公式サイト](https://mmdagent-ex.dev/download/) からWindows版のMMDAgent-EXが入ったzipファイルをダウンロード （ver2.0のzipファイルへの直リンクは[こちら](https://mmdagent.lee-lab.org/dl/app/MMDAgent-EX-2.0-20210116-win32.zip)）

1. ダウンロードしたzipファイルを `NH-chat/tools ` 以下に展開する

1. `NH-chat/tools/MMDAgent_Example.fst` と `NH-chat/tools/MMDAgent_Example.mdf` を MMDAgent_Example-1.4 に配置する（既存のファイルを置き換える）

## NH-chat 用の設定・変更点
1. MMDAgent-EXでは、文字コードが Shift-JIS から UTF-8 に変更されているため、ログを受け取る部分など、インターフェース部分で扱う文字コードも変更

1. `src/refData/path.csv` に MMDAgent-EXのパスを追加し、 `nh_path.path["MMDAgent"]` を呼び出しているところを `nh_path.path["MMDAgent-EX"]` に変更

    ```
    MMDAgent-EX,../../tools/MMDAgent-EX-2.0-20210116-win32,MMDAgent-EX.exeがあるフォルダ
    ```

1. `src/Interface/tools.py` でMMDAgent実行中の時にタスクをKillする部分の、対象タスクを `MMDAgent` から `MMDAgent-EX` に変更

1. MMDAgent_Example.mdf 内に設定を追加し、MMDAgent 1.4バージョンと挙動を合わせる

    ```
    # Socketプラグインを有効化（MMDAgent-EXには機能が内蔵されている）
    Plugin_Remote_EnableServer=true
    Plugin_Remote_Port=39390 # defaultは39392

    # 字幕の削除（デフォルトは字幕が表示される）
    show_caption=false

    # 内蔵されているJuliusを無効化
    exclude_Plugin_Julius=yes
    ```
