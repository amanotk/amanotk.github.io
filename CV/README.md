# CV

## コンパイル手順

```
  $ latexmk -lualatex -r latexmkrc
```

(latexmkrcはoverleaf用)

## Webに公開

```
  $ make
```

../../public/filesに出来たPDFファイルをコピーする．

## 環境設定

欧文フォントにGoogleのNotoフォントを使っているのでシステムに
インストールする必要がある．以下のようにすれば多分OK．
(Ubuntu 16.04で確認済み）

```
  $ wget http://mirrors.ctan.org/install/fonts/noto.tds.zip
  $ cd /usr/share/texmf
  $ sudo unzip ~/noto.tds.zip
  $ sudo mktexlsr
```

* HaranoAjiフォントはカレントディレクトリのフォントを用いる．

## publication.bib の再生成

文献リストの正本は Zotero．`publication.bib` は手で編集せず，
Zotero を更新してからスクリプトで再生成する．

```
  $ export ZOTERO_API_KEY=<Zotero の API キー（読み取り権限）>
  $ python3 zotero_to_bib.py            # 再生成して変更概要を表示
  $ python3 zotero_to_bib.py --dry-run  # 変更概要だけ見る
```

キーなしでやる場合は，手元で Zotero（デスクトップ版）を起動した状態で
`python3 zotero_to_bib.py --local` とすると，ローカル API 経由で
キー不要で再生成できる．非公開ライブラリは Web API では
キーなしで読めない（403 になる）ので，キーを作りたくない場合は
こちらを使う．

既存の citation key は DOI とタイトルで照合して引き継ぐので，
`CV-Amano.tex` の `\bibentry{...}` はそのまま使える．
新しい論文を Zotero に追加したら，tex 側に `\bibentry{キー}` を
足すこと（キーはスクリプトの変更概要と生成された bib で確認）．
