# amanotk.github.io

MkDocs Material + `uv` で管理する個人サイトです。英語版をルート (`/`)、日本語版を `/ja/` に公開します。

## ローカルプレビュー

```bash
uv sync
uv run mkdocs serve
```

ブラウザで `http://127.0.0.1:8000/` を開いて確認します。

## ビルド

```bash
uv run mkdocs build --strict
```

生成物は `site/` に出力されます。`site/` は Git 管理しません。

## CV の更新

CV の PDF は生成物として扱います。ローカル確認や GitHub Pages デプロイ時には `CV/` 側で PDF を作り、公開用ファイル `docs/assets/files/CV-Amano.pdf` を生成します。PDF 自体は Git 管理しません。

```bash
make -C CV
```

`make -C CV` は `CV/CV-Amano.tex` から PDF を生成し、サイト用の `docs/assets/files/CV-Amano.pdf` にコピーします。

## デプロイ

`main` ブランチへの push で GitHub Actions が LaTeX 環境をセットアップして CV PDF を生成し、その後 `mkdocs build --strict` を実行して GitHub Pages へデプロイします。

## ディレクトリ構成

- `docs/en/`: 英語コンテンツ
- `docs/ja/`: 日本語コンテンツ
- `docs/assets/`: 画像や PDF などの共通アセット
- `.github/workflows/pages.yml`: GitHub Pages デプロイ設定
