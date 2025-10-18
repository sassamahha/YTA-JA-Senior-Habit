YTA-ja-senior-habits automation and content rendering toolkit.

## セットアップ

ローカルでスクリプトを動かす場合は、Python 3.11 以上の仮想環境を作成し、以下のコマンドで依存関係をインストールしてください。

```
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install moviepy pillow numpy pyyaml
```

## トラブルシューティング

`ModuleNotFoundError: No module named 'moviepy.editor'` などの依存ライブラリに関するエラーが出た場合は、上記のインストール手順を再実行してから `python scripts/render.py <markdownファイル>` を実行してください。
