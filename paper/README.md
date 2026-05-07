# Paper

LaTeX skeleton for the methodology paper.

## Build

```bash
cd paper
pdflatex main
bibtex main
pdflatex main
pdflatex main
```

Or with `latexmk`:

```bash
latexmk -pdf main.tex
```

## Switching to the SBC template

`main.tex` currently uses the stock `article` class so the document compiles
out-of-the-box. To submit to an SBC venue (ENIAC, BRACIS, etc.):

1. Download `sbc-template.cls`, `sbc-template.bst`, and the SBC logo from
   https://www.sbc.org.br (look for "Templates para Artigos").
2. Drop the files into this directory.
3. In `main.tex`, replace
   ```latex
   \documentclass[11pt,a4paper]{article}
   ```
   with
   ```latex
   \documentclass[12pt]{sbc-template}
   ```
4. Replace `\bibliographystyle{abbrv}` with `\bibliographystyle{sbc}`.
5. Adjust `\title{}`, `\author{}`, and any `\address{}` macros to the SBC
   conventions (the SBC class redefines them).

The section files under `sections/` are class-agnostic and need no edits.

## Layout

```
paper/
├── main.tex             # entry point with title/author/abstract
├── sections/
│   ├── 01-introduction.tex
│   ├── 02-theoretical-framework.tex
│   ├── 03-related-work.tex
│   ├── 04-methodology.tex
│   ├── 05-results.tex
│   └── 06-conclusion.tex
├── references.bib       # 4 mandatory books + dataset refs
└── figures/             # PNGs from data/processed/figures (link or copy)
```

## Rubric mapping (10 pts total)

| File / Section                    | Rubric §                         | Pts |
|-----------------------------------|----------------------------------|-----|
| `main.tex` (`\title`, abstract)   | §2 Title and Abstract            | 0.5 |
| Conference choice in `main.tex`   | §1 Conference Qualis             | 0.5 |
| `01-introduction.tex`             | §3 Introduction                  | 1.0 |
| `02-theoretical-framework.tex`    | §4 Theoretical Framework         | 1.0 |
| `03-related-work.tex`             | §5 Related Work                  | 1.0 |
| `04-methodology.tex` + `05-results.tex` | §6 Development             | 4.0 |
| `06-conclusion.tex`               | §7 Conclusions                   | 1.0 |
| `references.bib`                  | §8 References                    | 1.0 |
