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

CV を更新する場合は先に `CV/` 側で PDF を作り、公開用ファイルを `docs/assets/files/CV-Amano.pdf` に反映します。

```bash
cd CV
make
```

## デプロイ

`main` ブランチへの push で GitHub Actions が `mkdocs build --strict` を実行し、その成果物を GitHub Pages へデプロイします。

## ディレクトリ構成

- `docs/en/`: 英語コンテンツ
- `docs/ja/`: 日本語コンテンツ
- `docs/assets/`: 画像や PDF などの共通アセット
- `.github/workflows/pages.yml`: GitHub Pages デプロイ設定
