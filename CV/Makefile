# -*- Makefile -*-

OUTPUT := ../docs/assets/files/CV-Amano.pdf

.PHONY: default cv clean

default: cv

cv:
	latexmk -r latexmkrc -lualatex CV-Amano.tex
	mkdir -p $(dir $(OUTPUT))
	cp -f CV-Amano.pdf $(OUTPUT)

clean:
	latexmk -C -r latexmkrc CV-Amano.tex
	rm -f CV-Amano.synctex.gz CV-Amano.bak0 $(OUTPUT)
