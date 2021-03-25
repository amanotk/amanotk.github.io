# メモ

## プレビュー
ローカルサーバーでプレビューするには

```bash
  $ hugo server
```

して．https://localhost:1313/ にアクセスする．  
サーバーがファイルの更新を自動でモニタしてくれる．

## public更新
CVを更新した場合は先にCVでMakeしてからpublicを更新する．

```bash
  $ cd CV
  $ make
  $ cd ..
  $ hugo -D
```

## githubにpush
ローカルでcommitした更新は以下のようにgithubにpushする．

```bash
  $ git push
  $ git submodule foreach git push
```

## submodule
submoduleがアップデートされた場合は別途commitが必要．

- public => 公開用
- theme/academic => テーマ
