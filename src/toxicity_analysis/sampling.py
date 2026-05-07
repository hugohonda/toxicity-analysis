"""Probabilistic sampling utilities (Cochran 1977; Bolfarine & Bussab 2005)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from math import ceil

import pandas as pd
from scipy.stats import norm


@dataclass(frozen=True)
class CochranResult:
    n0: float
    n: int
    z: float
    N: int | None
    e: float
    conf: float
    p: float


def calc_cochran(
    N: int | None = None,
    e: float = 0.05,
    conf: float = 0.95,
    p: float = 0.5,
) -> CochranResult:
    """Cochran (1977) sample size for proportions.

    n0 = z² · p · (1 − p) / e²
    n  = n0 / (1 + (n0 − 1) / N)    if N is finite (finite-population correction)

    Parameters
    ----------
    N
        Population size. ``None`` ⇒ infinite population (no FPC applied).
    e
        Margin of error, in (0, 1).
    conf
        Two-sided confidence level, in (0, 1).
    p
        A-priori proportion estimate. ``0.5`` maximises variance and is the
        conservative default when no prior estimate exists.
    """
    if not 0 < e < 1:
        raise ValueError("e must be in (0, 1)")
    if not 0 < conf < 1:
        raise ValueError("conf must be in (0, 1)")
    if not 0 <= p <= 1:
        raise ValueError("p must be in [0, 1]")
    if N is not None and N <= 0:
        raise ValueError("N must be positive when provided")

    z = float(norm.ppf(1 - (1 - conf) / 2))
    n0 = (z * z) * p * (1 - p) / (e * e)
    n_unrounded = n0 if N is None else n0 / (1 + (n0 - 1) / N)
    return CochranResult(n0=n0, n=ceil(n_unrounded), z=z, N=N, e=e, conf=conf, p=p)


def proportional_allocation(
    population: pd.DataFrame,
    stratum_col: str,
    n: int,
) -> dict[object, int]:
    """Bolfarine & Bussab (2005) proportional allocation.

    Returns per-stratum sample sizes ``n_h`` such that ``n_h / n ≈ N_h / N``,
    summing exactly to ``n`` via the largest-remainder rule.
    """
    if n <= 0:
        raise ValueError("n must be positive")
    if stratum_col not in population.columns:
        raise KeyError(f"stratum column not found: {stratum_col!r}")

    counts = population[stratum_col].value_counts()
    total = int(counts.sum())
    raw = counts * n / total
    integer = raw.astype(int)
    remainders = (raw - integer).sort_values(ascending=False, kind="stable")
    deficit = n - int(integer.sum())
    for label in remainders.index[:deficit]:
        integer[label] += 1
    return integer.to_dict()


def per_stratum_cochran_allocation(
    population: pd.DataFrame,
    stratum_col: str,
    e: float = 0.05,
    conf: float = 0.95,
    p: float = 0.5,
) -> dict[object, int]:
    """Per-stratum Cochran allocation with census of small strata (Cochran 1977 §5.5).

    For each stratum h, ``n_h = min(N_h, Cochran(N_h, e, conf, p))``. Strata
    too small to support the requested precision become a census draw.

    This is the recommended allocation for extreme-imbalance corpora where
    proportional allocation rounds rare strata to zero.
    """
    counts = population[stratum_col].value_counts()
    return {
        label: min(int(N_h), calc_cochran(N=int(N_h), e=e, conf=conf, p=p).n)
        for label, N_h in counts.items()
    }


def draw_stratified(
    population: pd.DataFrame,
    stratum_col: str,
    allocation: Mapping[object, int],
    *,
    random_state: int | None = None,
) -> pd.DataFrame:
    """Draw a stratified sample without replacement following ``allocation``.

    Allocation is a mapping ``stratum -> n_h``. Strata with ``n_h == 0`` are
    skipped; strata where ``n_h > N_h`` raise ``ValueError``.
    """
    parts: list[pd.DataFrame] = []
    for stratum, k in allocation.items():
        if k <= 0:
            continue
        pool = population[population[stratum_col] == stratum]
        if k > len(pool):
            raise ValueError(
                f"stratum {stratum!r} has {len(pool)} rows but allocation requests {k}"
            )
        parts.append(pool.sample(k, random_state=random_state, replace=False))
    if not parts:
        return population.iloc[0:0].copy()
    return (
        pd.concat(parts)
        .sample(frac=1, random_state=random_state)
        .reset_index(drop=True)
    )


def stratified_sample(
    population: pd.DataFrame,
    stratum_col: str,
    n: int,
    *,
    random_state: int | None = None,
) -> pd.DataFrame:
    """Proportional stratified sample of size ``n`` (without replacement)."""
    sizes = proportional_allocation(population, stratum_col, n)
    return draw_stratified(population, stratum_col, sizes, random_state=random_state)


def neyman_allocation(
    population: pd.DataFrame,
    stratum_col: str,
    y_col: str,
    n: int,
) -> dict[object, int]:
    """Neyman optimal allocation for a continuous target ``y``.

    Minimises ``Var(\\hat{\\bar{y}}_{st})`` for fixed total ``n``:

        n_h \\propto N_h * sigma_h

    where ``sigma_h`` is the population standard deviation of ``y`` within
    stratum ``h`` (Cochran 1977, §5.5; Bolfarine & Bussab 2005, §5.5).

    The allocation is capped at ``N_h`` per stratum (a stratum cannot be
    sampled more than its size) and balanced to sum to ``n`` via the
    largest-remainder rule. When ``sigma_h == 0`` for some stratum (no
    within-stratum variability), Neyman would assign 0 — we keep that
    behaviour, since the stratum carries no variance to reduce.
    """
    if n <= 0:
        raise ValueError("n must be positive")
    if stratum_col not in population.columns:
        raise KeyError(f"stratum column not found: {stratum_col!r}")
    if y_col not in population.columns:
        raise KeyError(f"y column not found: {y_col!r}")

    grouped = population.groupby(stratum_col, observed=True)[y_col]
    counts = grouped.size()
    sigmas = grouped.std(ddof=1).fillna(0.0)
    weights = counts.astype(float) * sigmas

    total = float(weights.sum())
    if total == 0.0:
        return {label: 0 for label in counts.index}

    raw = weights * n / total
    integer = raw.astype(int)
    integer = pd.Series(
        [min(int(integer[k]), int(counts[k])) for k in integer.index],
        index=integer.index,
    )
    deficit = n - int(integer.sum())
    if deficit > 0:
        room = (counts - integer).clip(lower=0)
        remainders = (raw - integer).where(room > 0, other=-1.0)
        order = remainders.sort_values(ascending=False, kind="stable").index
        for label in order:
            if deficit <= 0:
                break
            if integer[label] < counts[label]:
                integer[label] += 1
                deficit -= 1
    return integer.to_dict()
