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
