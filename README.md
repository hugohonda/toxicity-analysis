# toxicity-analysis

Análise de dados sobre conjuntos de toxicidade — base do artigo de mestrado sobre amostragem probabilística estratificada aplicada à auditoria de modelos de linguagem.

## Pré-requisitos

Requer [uv](https://docs.astral.sh/uv/) e Python 3.12+.

```bash
uv sync
```

## Dados

Conjunto principal: [**ToLD-Br**](https://huggingface.co/datasets/mteb/told-br) — *Toxic Language Detection in Brazilian Portuguese* (Leite et al. 2020). 21.000 tweets em português brasileiro, anotados em 6 categorias de dano (`homophobia`, `obscene`, `insult`, `racism`, `misogyny`, `xenophobia`), cada uma com uma pontuação 0–3 correspondente ao número de anotadores (de 3) que sinalizaram a categoria.

Para baixar uma única vez em `data/raw/told-br/train.csv`:

```bash
uv run python -c "from datasets import load_dataset; \
  load_dataset('mteb/told-br')['train'].to_csv('data/raw/told-br/train.csv', index=False)"
```

Não há necessidade de autenticação no HuggingFace — o dataset é público.

## Uso

Abrir o Jupyter Lab:

```bash
uv run jupyter lab
```

Rodar testes e *linting*:

```bash
uv run pytest
uv run ruff check .
uv run ruff format .
```

## Estrutura

```
data/
  raw/         # dados brutos imutáveis (gitignored)
  processed/   # datasets derivados e figuras (gitignored)
notebooks/     # análises exploratórias (PT-BR)
src/toxicity_analysis/
               # código reutilizável (amostragem, features, estimadores)
tests/         # suite pytest
paper/         # esqueleto LaTeX do artigo (template SBC)
```

## Notebooks

- `01_toldbr_eda.ipynb` — exploração inicial (esquema, valores ausentes, distribuição de classes, comprimento de texto, exemplos das caudas raras).
- `02_features_validation.ipynb` — *features* léxicas + validação população vs. amostra Fix B (Cochran-por-estrato com censo).
- `03_estimators.ipynb` — alocação de Neyman + estimadores tipo razão e tipo regressão (em construção).

## Módulo `toxicity_analysis`

- `constants.py` — constantes do dataset (rótulos, limiar de maioria).
- `sampling.py` — fórmula de Cochran (1977), alocação proporcional (Bolfarine & Bussab 2005), Cochran-por-estrato com censo (§5.5), e amostragem estratificada sem reposição.
- `features.py` — *features* léxicas determinísticas (`word_count`, `unique_word_ratio`, `caps_ratio`, `punc_density`, `mean_word_length`) e diagnóstico de ruído de anotação por categoria.
- `estimators.py` — estimadores tipo razão e tipo regressão sob desenho estratificado (em construção).
