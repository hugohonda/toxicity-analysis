"""Lexical and noise features for toxicity datasets.

Layer 1: deterministic per-row lexical features (word_count, caps_ratio, ...).
Layer 3: annotator-vote noise diagnostics for ToLD-Br's ordinal scheme.
"""

from __future__ import annotations

import re
import string
from collections.abc import Iterable

import numpy as np
import pandas as pd

from toxicity_analysis.constants import TOLDBR_LABELS, TOLDBR_MAJORITY_THRESHOLD

_PUNCT = frozenset(string.punctuation)
_WORD_RE = re.compile(r"\b\w+\b", flags=re.UNICODE)


def _word_count(text: str) -> int:
    return len(_WORD_RE.findall(text))


def _unique_word_ratio(text: str) -> float:
    words = _WORD_RE.findall(text.lower())
    return len(set(words)) / len(words) if words else 0.0


def _caps_ratio(text: str) -> float:
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return 0.0
    return sum(1 for c in letters if c.isupper()) / len(letters)


def _punc_density(text: str) -> float:
    if not text:
        return 0.0
    return sum(1 for c in text if c in _PUNCT) / len(text)


def _mean_word_length(text: str) -> float:
    words = _WORD_RE.findall(text)
    return float(np.mean([len(w) for w in words])) if words else 0.0


def add_lexical_features(
    df: pd.DataFrame,
    text_col: str = "text",
) -> pd.DataFrame:
    """Append five deterministic lexical features as new columns.

    Columns added: ``word_count``, ``unique_word_ratio``, ``caps_ratio``,
    ``punc_density``, ``mean_word_length``. The input frame is not mutated.
    """
    if text_col not in df.columns:
        raise KeyError(f"text column not found: {text_col!r}")

    out = df.copy()
    text = out[text_col].astype(str)
    out["word_count"] = text.map(_word_count)
    out["unique_word_ratio"] = text.map(_unique_word_ratio)
    out["caps_ratio"] = text.map(_caps_ratio)
    out["punc_density"] = text.map(_punc_density)
    out["mean_word_length"] = text.map(_mean_word_length)
    return out


def feature_summary(
    df: pd.DataFrame,
    feature_cols: Iterable[str],
    group_col: str | None = None,
) -> pd.DataFrame:
    """Mean ± standard error of the mean per feature, optionally grouped.

    SE = σ / √n is reported (Cochran 1977 §2.6) so the table is directly
    usable for the population vs. sample comparison in the Development
    section.
    """
    cols = list(feature_cols)
    if group_col is None:
        means = df[cols].mean()
        sems = df[cols].sem(ddof=1)
        return pd.DataFrame({"mean": means, "sem": sems, "n": len(df)})

    grouped = df.groupby(group_col, observed=True)
    means = grouped[cols].mean()
    sems = grouped[cols].sem(ddof=1)
    counts = grouped.size().rename("n")
    out = (
        means.add_suffix("_mean")
        .join(sems.add_suffix("_sem"))
        .join(counts)
    )
    return out


def vote_noise_breakdown(
    df: pd.DataFrame,
    labels: Iterable[str] = TOLDBR_LABELS,
    threshold: int = TOLDBR_MAJORITY_THRESHOLD,
) -> pd.DataFrame:
    """Per-category vote-count breakdown for ToLD-Br-style ordinal labels.

    Returns one row per category with the count at each vote level
    (0/1/2/3) plus the share that the majority rule (``votes >= threshold``)
    excludes as "disputed" (vote == 1).

    The "disputed" share is a label-noise diagnostic: tweets where exactly
    one of three annotators flagged the category are neither cleanly
    negative nor cleanly positive under the majority rule, but they would
    flip to positive under a stricter threshold.
    """
    levels = [0, 1, 2, 3]
    rows: list[dict[str, object]] = []
    for label in labels:
        counts = df[label].value_counts().reindex(levels, fill_value=0).astype(int)
        positives = int((df[label] >= threshold).sum())
        rows.append({
            "category": label,
            **{f"votes_{lvl}": int(counts[lvl]) for lvl in levels},
            "positives_majority": positives,
            "disputed_share": float(counts[1]) / len(df) if len(df) else 0.0,
        })
    return pd.DataFrame(rows).set_index("category")
