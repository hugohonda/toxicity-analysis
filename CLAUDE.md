# CLAUDE.md

Guidance for Claude Code working in this repo.

## Project

Data analysis on toxicity datasets. Python 3.12, managed with `uv`.

## Commands

- Install / sync deps: `uv sync`
- Add a runtime dep: `uv add <pkg>`
- Add a dev dep: `uv add --dev <pkg>`
- Run a script: `uv run python -m toxicity_analysis`
- Jupyter: `uv run jupyter lab`
- Tests: `uv run pytest`
- Lint / format: `uv run ruff check .` / `uv run ruff format .`

Always run Python via `uv run` so the project env is used.

## Layout

- `data/raw/told-br/train.csv` — ToLD-Br (Brazilian Portuguese, 21k tweets, 6 harm categories, ordinal 0–3 votes). Download steps in README.md. Gitignored.
- `data/raw/` — other immutable inputs, gitignored.
- `data/processed/` — derived datasets and figures, gitignored. Regenerate from `raw/`.
- `notebooks/` — exploratory work; keep one notebook per question.
- `src/toxicity_analysis/` — reusable code imported by notebooks and scripts.
- `tests/` — pytest tests for code in `src/`.
- `paper/` — LaTeX skeleton (article class by default, SBC swap documented in `paper/README.md`). Sections under `paper/sections/`, bib at `paper/references.bib`.

## Dataset schema (ToLD-Br)

- `text` — tweet text (Brazilian Portuguese)
- 6 harm columns, each int 0–3 = number of annotator votes (out of 3): `homophobia`, `obscene`, `insult`, `racism`, `misogyny`, `xenophobia`
- A common binarisation rule is `label_bin = (votes >= 2)` (majority of annotators agreed).

## Conventions

- Put reusable logic in `src/toxicity_analysis/` and import it from notebooks; do not let analysis logic live only inside `.ipynb` files.
- Treat `data/raw/` as read-only. Write derived data to `data/processed/`.
- Do not commit datasets, model artifacts, or notebook outputs containing data.

## Paper-writing rules

- **Never mention generative AI / LLM / Claude / ChatGPT / "AI assistant" anywhere in `paper/`.** Do not add disclosure sections, acknowledgements, or methodological notes about AI-assisted writing. The paper must read as the authors' independent work.
- All paper-facing text in PT-BR; source code, tests, and CLAUDE.md stay in English.
