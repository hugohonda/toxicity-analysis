"""Stratified estimators for population mean Ȳ.

Implements three estimators with variance approximations under stratified
random sampling without replacement (Cochran 1977, ch. 5–7;
Bolfarine & Bussab 2005, ch. 5–7):

- ``stratified_mean_estimator`` — baseline ``ȳ_st = Σ W_h ȳ_h``.
- ``stratified_ratio_estimator`` — ratio with auxiliary x (separate / combined).
- ``stratified_regression_estimator`` — regression with auxiliary x (separate / combined).

All return an :class:`Estimate` with the point value, large-sample variance,
standard error, and a 95% Wald confidence interval. The auxiliary input
``X_pop_total`` (population total of x) is required; ``X_pop_per_stratum``
is required only for *separate* ratio/regression.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from math import sqrt
from typing import Literal

import pandas as pd
from scipy.stats import norm


@dataclass(frozen=True)
class Estimate:
    point: float
    variance: float
    se: float
    ci_low: float
    ci_high: float
    name: str = ""

    @classmethod
    def from_point_variance(cls, point: float, variance: float, name: str = "") -> Estimate:
        if variance < 0:
            variance = 0.0
        se = sqrt(variance)
        z = float(norm.ppf(0.975))
        return cls(
            point=point,
            variance=variance,
            se=se,
            ci_low=point - z * se,
            ci_high=point + z * se,
            name=name,
        )


def _stratum_stats(
    sample: pd.DataFrame,
    population: pd.DataFrame,
    stratum_col: str,
    cols: tuple[str, ...],
) -> pd.DataFrame:
    """Per-stratum sample sizes, sample means, sample (co)variances, and N_h."""
    N_h = population[stratum_col].value_counts().rename("N_h")
    grouped = sample.groupby(stratum_col, observed=True)
    n_h = grouped.size().rename("n_h")
    means = grouped[list(cols)].mean().add_prefix("mean_")
    var = grouped[list(cols)].var(ddof=1).fillna(0.0).add_prefix("var_")
    out = pd.concat([N_h, n_h, means, var], axis=1).dropna(subset=["n_h"])
    out["W_h"] = out["N_h"] / out["N_h"].sum()
    out["f_h"] = out["n_h"] / out["N_h"]
    return out


def _stratum_covariance(
    sample: pd.DataFrame,
    stratum_col: str,
    x_col: str,
    y_col: str,
) -> pd.Series:
    """Per-stratum sample covariance Cov(x, y) with ddof=1."""
    grouped = sample.groupby(stratum_col, observed=True)
    cov = grouped.apply(
        lambda g: g[[x_col, y_col]].cov(ddof=1).iloc[0, 1] if len(g) > 1 else 0.0,
        include_groups=False,
    )
    return cov.rename("cov_xy").fillna(0.0)


def stratified_mean_estimator(
    sample: pd.DataFrame,
    population: pd.DataFrame,
    stratum_col: str,
    y_col: str,
) -> Estimate:
    """Stratified sample mean with FPC variance (Cochran §5.5).

    Ȳ_st = Σ W_h ȳ_h
    Var(Ȳ_st) = Σ W_h^2 · (1 − f_h) · s²_yh / n_h
    """
    stats = _stratum_stats(sample, population, stratum_col, (y_col,))
    point = float((stats["W_h"] * stats[f"mean_{y_col}"]).sum())
    variance = float(
        (
            stats["W_h"] ** 2
            * (1 - stats["f_h"])
            * stats[f"var_{y_col}"]
            / stats["n_h"]
        ).sum()
    )
    return Estimate.from_point_variance(point, variance, name="stratified_mean")


def stratified_ratio_estimator(
    sample: pd.DataFrame,
    population: pd.DataFrame,
    stratum_col: str,
    x_col: str,
    y_col: str,
    X_pop_total: float,
    *,
    mode: Literal["separate", "combined"] = "separate",
) -> Estimate:
    """Stratified ratio estimator for Ȳ.

    Separate (Cochran §6.10): Ŷ_Rs = Σ W_h · (ȳ_h / x̄_h) · X̄_h
        Var ≈ Σ W_h² · (1 − f_h) / n_h · (s²_yh − 2 R_h s_xyh + R_h² s²_xh),
        with R_h = ȳ_h / x̄_h.
    Combined (Cochran §6.11): Ŷ_Rc = (ȳ_st / x̄_st) · X̄
        Var ≈ Σ W_h² · (1 − f_h) / n_h · (s²_yh − 2 R s_xyh + R² s²_xh),
        with R = ȳ_st / x̄_st.
    """
    stats = _stratum_stats(sample, population, stratum_col, (x_col, y_col))
    cov = _stratum_covariance(sample, stratum_col, x_col, y_col)
    stats["cov_xy"] = cov.reindex(stats.index, fill_value=0.0)

    N = float(stats["N_h"].sum())
    X_bar_pop = X_pop_total / N

    if mode == "separate":
        X_bar_h = population.groupby(stratum_col, observed=True)[x_col].mean()
        R_h = stats[f"mean_{y_col}"] / stats[f"mean_{x_col}"]
        point = float((stats["W_h"] * R_h * X_bar_h.reindex(stats.index)).sum())
        variance = float(
            (
                stats["W_h"] ** 2
                * (1 - stats["f_h"])
                / stats["n_h"]
                * (
                    stats[f"var_{y_col}"]
                    - 2 * R_h * stats["cov_xy"]
                    + (R_h**2) * stats[f"var_{x_col}"]
                )
            ).sum()
        )
        name = "ratio_separate"
    elif mode == "combined":
        y_st = float((stats["W_h"] * stats[f"mean_{y_col}"]).sum())
        x_st = float((stats["W_h"] * stats[f"mean_{x_col}"]).sum())
        R = y_st / x_st
        point = R * X_bar_pop
        variance = float(
            (
                stats["W_h"] ** 2
                * (1 - stats["f_h"])
                / stats["n_h"]
                * (
                    stats[f"var_{y_col}"]
                    - 2 * R * stats["cov_xy"]
                    + (R**2) * stats[f"var_{x_col}"]
                )
            ).sum()
        )
        name = "ratio_combined"
    else:
        raise ValueError(f"mode must be 'separate' or 'combined', got {mode!r}")

    return Estimate.from_point_variance(point, variance, name=name)


def stratified_regression_estimator(
    sample: pd.DataFrame,
    population: pd.DataFrame,
    stratum_col: str,
    x_col: str,
    y_col: str,
    X_pop_total: float,
    *,
    mode: Literal["separate", "combined"] = "separate",
) -> Estimate:
    """Stratified regression estimator for Ȳ.

    Separate (Cochran §7.10): Ŷ_lrs = Σ W_h · [ȳ_h + b_h · (X̄_h − x̄_h)],
        b_h = s_xyh / s²_xh.
        Var ≈ Σ W_h² · (1 − f_h) / n_h · s²_yh · (1 − r_h²).
    Combined (Cochran §7.11): Ŷ_lrc = ȳ_st + b · (X̄ − x̄_st),
        b = Σ W_h² · (1 − f_h) · s_xyh / n_h
            ÷  Σ W_h² · (1 − f_h) · s²_xh / n_h.
    """
    stats = _stratum_stats(sample, population, stratum_col, (x_col, y_col))
    cov = _stratum_covariance(sample, stratum_col, x_col, y_col)
    stats["cov_xy"] = cov.reindex(stats.index, fill_value=0.0)

    N = float(stats["N_h"].sum())
    X_bar_pop = X_pop_total / N

    if mode == "separate":
        X_bar_h = population.groupby(stratum_col, observed=True)[x_col].mean()
        var_x = stats[f"var_{x_col}"].replace(0.0, float("nan"))
        b_h = (stats["cov_xy"] / var_x).fillna(0.0)
        adjustment = b_h * (X_bar_h.reindex(stats.index) - stats[f"mean_{x_col}"])
        point = float((stats["W_h"] * (stats[f"mean_{y_col}"] + adjustment)).sum())

        # 1 − r_h^2; clip to [0, 1] guards numerical drift.
        denom = (stats[f"var_{y_col}"] * stats[f"var_{x_col}"]).replace(0.0, float("nan"))
        r2 = ((stats["cov_xy"] ** 2) / denom).fillna(0.0).clip(lower=0.0, upper=1.0)
        variance = float(
            (
                stats["W_h"] ** 2
                * (1 - stats["f_h"])
                / stats["n_h"]
                * stats[f"var_{y_col}"]
                * (1 - r2)
            ).sum()
        )
        name = "regression_separate"
    elif mode == "combined":
        weights = stats["W_h"] ** 2 * (1 - stats["f_h"]) / stats["n_h"]
        num = float((weights * stats["cov_xy"]).sum())
        den = float((weights * stats[f"var_{x_col}"]).sum())
        b = num / den if den > 0 else 0.0
        y_st = float((stats["W_h"] * stats[f"mean_{y_col}"]).sum())
        x_st = float((stats["W_h"] * stats[f"mean_{x_col}"]).sum())
        point = y_st + b * (X_bar_pop - x_st)

        residual_var = (
            stats[f"var_{y_col}"]
            - 2 * b * stats["cov_xy"]
            + (b**2) * stats[f"var_{x_col}"]
        ).clip(lower=0.0)
        variance = float(
            (
                stats["W_h"] ** 2
                * (1 - stats["f_h"])
                / stats["n_h"]
                * residual_var
            ).sum()
        )
        name = "regression_combined"
    else:
        raise ValueError(f"mode must be 'separate' or 'combined', got {mode!r}")

    return Estimate.from_point_variance(point, variance, name=name)


def compare_estimators(
    sample: pd.DataFrame,
    population: pd.DataFrame,
    stratum_col: str,
    x_col: str,
    y_col: str,
) -> pd.DataFrame:
    """Run all five estimators of Ȳ and return a comparison frame.

    Includes the population mean as the ground truth (last row) so the paper
    can directly report bias and standard error per estimator.
    """
    X_pop_total = float(population[x_col].sum())
    estimates: list[Estimate] = [
        stratified_mean_estimator(sample, population, stratum_col, y_col),
        stratified_ratio_estimator(
            sample, population, stratum_col, x_col, y_col, X_pop_total, mode="separate"
        ),
        stratified_ratio_estimator(
            sample, population, stratum_col, x_col, y_col, X_pop_total, mode="combined"
        ),
        stratified_regression_estimator(
            sample, population, stratum_col, x_col, y_col, X_pop_total, mode="separate"
        ),
        stratified_regression_estimator(
            sample, population, stratum_col, x_col, y_col, X_pop_total, mode="combined"
        ),
    ]
    truth = float(population[y_col].mean())
    rows: list[Mapping[str, object]] = []
    for est in estimates:
        rows.append({
            "estimator": est.name,
            "point": est.point,
            "se": est.se,
            "ci_low": est.ci_low,
            "ci_high": est.ci_high,
            "abs_error": abs(est.point - truth),
        })
    rows.append({
        "estimator": "population_mean",
        "point": truth,
        "se": float("nan"),
        "ci_low": float("nan"),
        "ci_high": float("nan"),
        "abs_error": 0.0,
    })
    return pd.DataFrame(rows).set_index("estimator")
