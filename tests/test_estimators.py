import numpy as np
import pandas as pd
import pytest

from toxicity_analysis.estimators import (
    Estimate,
    compare_estimators,
    stratified_mean_estimator,
    stratified_ratio_estimator,
    stratified_regression_estimator,
)


def _toy_population(seed: int = 0, n: int = 2_000) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    stratum = rng.choice(["a", "b", "c"], size=n, p=[0.6, 0.3, 0.1])
    x = rng.normal(loc=10.0, scale=2.0, size=n)
    y = 2 * x + rng.normal(loc=0.0, scale=1.0, size=n)
    return pd.DataFrame({"stratum": stratum, "x": x, "y": y})


def _draw_strs(df: pd.DataFrame, sizes: dict[str, int], seed: int = 42) -> pd.DataFrame:
    parts = [
        df[df["stratum"] == k].sample(v, random_state=seed)
        for k, v in sizes.items()
    ]
    return pd.concat(parts).reset_index(drop=True)


class TestEstimateContainer:
    def test_ci_width_matches_se(self):
        e = Estimate.from_point_variance(point=10.0, variance=4.0, name="x")
        assert e.se == 2.0
        assert e.ci_high - e.ci_low == pytest.approx(2 * 1.96 * 2.0, abs=0.05)

    def test_negative_variance_clipped(self):
        e = Estimate.from_point_variance(point=1.0, variance=-1e-12)
        assert e.variance == 0.0
        assert e.se == 0.0


class TestStratifiedMean:
    def test_recovers_population_mean_under_full_census(self):
        # Sampling everything ⇒ estimator equals population mean exactly.
        df = _toy_population()
        est = stratified_mean_estimator(df, df, "stratum", "y")
        assert est.point == pytest.approx(df["y"].mean(), abs=1e-9)
        assert est.variance == pytest.approx(0.0, abs=1e-9)

    def test_unbiased_on_small_sample(self):
        df = _toy_population()
        sample = _draw_strs(df, {"a": 60, "b": 30, "c": 10})
        est = stratified_mean_estimator(sample, df, "stratum", "y")
        truth = df["y"].mean()
        # within ~3 SE for a clean, well-behaved DGP.
        assert abs(est.point - truth) <= 3 * est.se


class TestStratifiedRatio:
    @pytest.mark.parametrize("mode", ["separate", "combined"])
    def test_recovers_population_mean_under_full_census(self, mode: str):
        df = _toy_population()
        X_pop_total = float(df["x"].sum())
        est = stratified_ratio_estimator(
            df, df, "stratum", "x", "y", X_pop_total, mode=mode
        )
        assert est.point == pytest.approx(df["y"].mean(), abs=1e-9)

    @pytest.mark.parametrize("mode", ["separate", "combined"])
    def test_in_ci_on_small_sample(self, mode: str):
        df = _toy_population()
        sample = _draw_strs(df, {"a": 80, "b": 50, "c": 20})
        X_pop_total = float(df["x"].sum())
        est = stratified_ratio_estimator(
            sample, df, "stratum", "x", "y", X_pop_total, mode=mode
        )
        truth = df["y"].mean()
        assert abs(est.point - truth) <= 3 * est.se

    def test_invalid_mode_raises(self):
        df = _toy_population()
        with pytest.raises(ValueError):
            stratified_ratio_estimator(
                df, df, "stratum", "x", "y", X_pop_total=1.0, mode="bogus",
            )


class TestStratifiedRegression:
    @pytest.mark.parametrize("mode", ["separate", "combined"])
    def test_recovers_population_mean_under_full_census(self, mode: str):
        df = _toy_population()
        X_pop_total = float(df["x"].sum())
        est = stratified_regression_estimator(
            df, df, "stratum", "x", "y", X_pop_total, mode=mode
        )
        assert est.point == pytest.approx(df["y"].mean(), abs=1e-9)

    @pytest.mark.parametrize("mode", ["separate", "combined"])
    def test_beats_simple_stratified_mean_when_x_correlated(self, mode: str):
        # On a DGP where y = 2x + noise, regression should be more precise
        # than the stratified mean (lower SE).
        df = _toy_population()
        sample = _draw_strs(df, {"a": 80, "b": 50, "c": 20})
        X_pop_total = float(df["x"].sum())
        baseline = stratified_mean_estimator(sample, df, "stratum", "y")
        reg = stratified_regression_estimator(
            sample, df, "stratum", "x", "y", X_pop_total, mode=mode
        )
        assert reg.se < baseline.se

    def test_invalid_mode_raises(self):
        df = _toy_population()
        with pytest.raises(ValueError):
            stratified_regression_estimator(
                df, df, "stratum", "x", "y", X_pop_total=1.0, mode="bogus",
            )


class TestCompareEstimators:
    def test_returns_six_rows(self):
        df = _toy_population()
        sample = _draw_strs(df, {"a": 80, "b": 50, "c": 20})
        out = compare_estimators(sample, df, "stratum", "x", "y")
        assert len(out) == 6
        assert "population_mean" in out.index
        assert out.loc["population_mean", "abs_error"] == 0.0

    def test_all_estimators_within_3_se_of_truth(self):
        df = _toy_population()
        sample = _draw_strs(df, {"a": 80, "b": 50, "c": 20})
        out = compare_estimators(sample, df, "stratum", "x", "y")
        truth = df["y"].mean()
        for name in out.index:
            if name == "population_mean":
                continue
            row = out.loc[name]
            assert abs(row["point"] - truth) <= 3 * row["se"], f"{name} too far"
