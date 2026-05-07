import numpy as np
import pandas as pd
import pytest

from toxicity_analysis.sampling import (
    calc_cochran,
    draw_stratified,
    neyman_allocation,
    per_stratum_cochran_allocation,
    proportional_allocation,
    stratified_sample,
)


class TestCalcCochran:
    def test_textbook_n0_at_95ci_p_half_e_05(self):
        # Cochran's classic example: n0 ≈ 384 at 95% CI, p=0.5, e=5%.
        r = calc_cochran(N=None, e=0.05, conf=0.95, p=0.5)
        assert r.z == pytest.approx(1.96, abs=0.01)
        assert r.n0 == pytest.approx(384.16, abs=0.5)

    def test_finite_correction_matches_toldbr(self):
        # ToLD-Br: N=21,000 ⇒ n=378 (ceil of 377.3).
        r = calc_cochran(N=21000, e=0.05, conf=0.95, p=0.5)
        assert r.n == 378

    def test_smaller_p_gives_smaller_n(self):
        n_half = calc_cochran(N=10_000, p=0.5).n
        n_low = calc_cochran(N=10_000, p=0.1).n
        assert n_low < n_half

    def test_larger_e_gives_smaller_n(self):
        n_strict = calc_cochran(N=10_000, e=0.03).n
        n_loose = calc_cochran(N=10_000, e=0.10).n
        assert n_loose < n_strict

    def test_higher_conf_gives_larger_n(self):
        n_95 = calc_cochran(N=10_000, conf=0.95).n
        n_99 = calc_cochran(N=10_000, conf=0.99).n
        assert n_99 > n_95

    def test_finite_correction_strictly_smaller_than_n0(self):
        r = calc_cochran(N=1_000)
        assert r.n < r.n0

    def test_infinite_population_skips_fpc(self):
        r = calc_cochran(N=None)
        assert r.n == pytest.approx(r.n0, abs=1)

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"e": 0},
            {"e": -0.1},
            {"e": 1.0},
            {"e": 1.5},
            {"conf": 0},
            {"conf": -0.1},
            {"conf": 1.0},
            {"p": -0.1},
            {"p": 1.1},
            {"N": 0},
            {"N": -1},
        ],
    )
    def test_invalid_inputs_raise(self, kwargs):
        with pytest.raises(ValueError):
            calc_cochran(**({"N": 1_000} | kwargs))


class TestProportionalAllocation:
    def test_sums_exactly_to_n(self):
        df = pd.DataFrame({"label": ["a"] * 800 + ["b"] * 150 + ["c"] * 50})
        sizes = proportional_allocation(df, "label", n=100)
        assert sum(sizes.values()) == 100

    def test_preserves_proportions_when_clean(self):
        df = pd.DataFrame({"label": ["a"] * 800 + ["b"] * 150 + ["c"] * 50})
        sizes = proportional_allocation(df, "label", n=100)
        assert sizes["a"] == 80
        assert sizes["b"] == 15
        assert sizes["c"] == 5

    def test_largest_remainder_resolves_rounding(self):
        # 3 strata of equal size, n=10 ⇒ {3,3,4} after largest-remainder.
        df = pd.DataFrame({"label": list("aaabbbccc")})
        sizes = proportional_allocation(df, "label", n=10)
        assert sum(sizes.values()) == 10
        assert sorted(sizes.values()) == [3, 3, 4]

    def test_invalid_n_raises(self):
        df = pd.DataFrame({"label": ["a", "b"]})
        with pytest.raises(ValueError):
            proportional_allocation(df, "label", n=0)

    def test_missing_stratum_column_raises(self):
        df = pd.DataFrame({"label": ["a", "b"]})
        with pytest.raises(KeyError):
            proportional_allocation(df, "nonexistent", n=5)


class TestStratifiedSample:
    def _toy(self, seed: int = 0) -> pd.DataFrame:
        rng = np.random.default_rng(seed)
        return pd.DataFrame({
            "label": rng.choice(["a", "b", "c"], size=1_000, p=[0.7, 0.2, 0.1]),
            "x": rng.normal(size=1_000),
        })

    def test_returns_exactly_n_rows(self):
        sample = stratified_sample(self._toy(), "label", n=200, random_state=42)
        assert len(sample) == 200

    def test_all_strata_represented_when_population_supports_it(self):
        sample = stratified_sample(self._toy(), "label", n=200, random_state=42)
        assert set(sample["label"].unique()) == {"a", "b", "c"}

    def test_proportions_close_to_population(self):
        df = self._toy()
        sample = stratified_sample(df, "label", n=200, random_state=42)
        pop = df["label"].value_counts(normalize=True)
        smp = sample["label"].value_counts(normalize=True)
        # within 1 row's worth of slack at this n.
        for k in pop.index:
            assert abs(smp[k] - pop[k]) <= 1 / 200

    def test_reproducible_with_random_state(self):
        df = self._toy()
        s1 = stratified_sample(df, "label", n=100, random_state=42)
        s2 = stratified_sample(df, "label", n=100, random_state=42)
        pd.testing.assert_frame_equal(s1, s2)

    def test_no_duplicates_drawn(self):
        df = self._toy().reset_index(drop=False).rename(columns={"index": "uid"})
        sample = stratified_sample(df, "label", n=200, random_state=42)
        assert sample["uid"].is_unique


class TestPerStratumCochranAllocation:
    def test_per_stratum_n_matches_calc_cochran(self):
        # 3 strata of distinct sizes: each n_h should equal Cochran(N_h)
        df = pd.DataFrame({
            "stratum": ["a"] * 5_000 + ["b"] * 1_000 + ["c"] * 200,
        })
        alloc = per_stratum_cochran_allocation(df, "stratum")
        assert alloc["a"] == calc_cochran(N=5_000).n
        assert alloc["b"] == calc_cochran(N=1_000).n
        assert alloc["c"] == calc_cochran(N=200).n

    def test_small_stratum_becomes_census(self):
        # N_h=20 is far smaller than Cochran's n0 ⇒ allocation == N_h.
        df = pd.DataFrame({"stratum": ["rare"] * 20 + ["common"] * 5_000})
        alloc = per_stratum_cochran_allocation(df, "stratum")
        assert alloc["rare"] == 20  # full census

    def test_total_exceeds_proportional_for_imbalanced_data(self):
        # The whole point of Fix B: pay more rows for tail precision.
        df = pd.DataFrame(
            {"stratum": ["a"] * 10_000 + ["b"] * 100 + ["c"] * 30}
        )
        prop_total = sum(proportional_allocation(df, "stratum", n=378).values())
        cochran_total = sum(per_stratum_cochran_allocation(df, "stratum").values())
        assert cochran_total > prop_total

    def test_invalid_inputs_propagate(self):
        df = pd.DataFrame({"stratum": ["a"] * 10})
        with pytest.raises(ValueError):
            per_stratum_cochran_allocation(df, "stratum", e=1.5)


class TestDrawStratified:
    def test_honours_arbitrary_allocation(self):
        df = pd.DataFrame({"label": ["a"] * 100 + ["b"] * 50})
        out = draw_stratified(df, "label", {"a": 10, "b": 5}, random_state=42)
        assert len(out) == 15
        assert (out["label"] == "a").sum() == 10
        assert (out["label"] == "b").sum() == 5

    def test_zero_allocation_strata_skipped(self):
        df = pd.DataFrame({"label": ["a"] * 100 + ["b"] * 50})
        out = draw_stratified(df, "label", {"a": 5, "b": 0}, random_state=42)
        assert len(out) == 5
        assert set(out["label"].unique()) == {"a"}

    def test_overdraw_raises(self):
        df = pd.DataFrame({"label": ["rare"] * 10})
        with pytest.raises(ValueError):
            draw_stratified(df, "label", {"rare": 50})

    def test_compose_with_per_stratum_cochran(self):
        rng = np.random.default_rng(0)
        df = pd.DataFrame({
            "label": rng.choice(["a", "b", "c"], size=2_000, p=[0.7, 0.25, 0.05]),
            "x": rng.normal(size=2_000),
        })
        alloc = per_stratum_cochran_allocation(df, "label")
        sample = draw_stratified(df, "label", alloc, random_state=42)
        assert len(sample) == sum(alloc.values())
        # every stratum populated (Fix B's whole point)
        assert set(sample["label"].unique()) == {"a", "b", "c"}


class TestNeymanAllocation:
    def test_sums_to_n(self):
        rng = np.random.default_rng(0)
        df = pd.DataFrame({
            "stratum": ["a"] * 500 + ["b"] * 300 + ["c"] * 200,
            "y": rng.normal(size=1_000),
        })
        alloc = neyman_allocation(df, "stratum", "y", n=100)
        assert sum(alloc.values()) == 100

    def test_higher_sigma_gets_larger_allocation(self):
        rng = np.random.default_rng(0)
        # equal stratum sizes; only sigma differs.
        y_a = rng.normal(scale=1.0, size=500)
        y_b = rng.normal(scale=4.0, size=500)
        df = pd.DataFrame({
            "stratum": ["a"] * 500 + ["b"] * 500,
            "y": np.concatenate([y_a, y_b]),
        })
        alloc = neyman_allocation(df, "stratum", "y", n=100)
        assert alloc["b"] > alloc["a"]

    def test_caps_at_stratum_size(self):
        rng = np.random.default_rng(0)
        # Tiny stratum with high sigma should be capped at N_h.
        df = pd.DataFrame({
            "stratum": ["a"] * 10 + ["b"] * 10_000,
            "y": np.concatenate([
                rng.normal(scale=100.0, size=10),
                rng.normal(scale=0.1, size=10_000),
            ]),
        })
        alloc = neyman_allocation(df, "stratum", "y", n=100)
        assert alloc["a"] <= 10  # cannot exceed stratum size

    def test_zero_variance_stratum_gets_zero(self):
        df = pd.DataFrame({
            "stratum": ["constant"] * 100 + ["varied"] * 100,
            "y": [5.0] * 100 + list(np.linspace(0, 10, 100)),
        })
        alloc = neyman_allocation(df, "stratum", "y", n=50)
        assert alloc["constant"] == 0
        assert alloc["varied"] == 50

    def test_invalid_inputs(self):
        df = pd.DataFrame({"stratum": ["a", "b"], "y": [1.0, 2.0]})
        with pytest.raises(ValueError):
            neyman_allocation(df, "stratum", "y", n=0)
        with pytest.raises(KeyError):
            neyman_allocation(df, "missing", "y", n=10)
        with pytest.raises(KeyError):
            neyman_allocation(df, "stratum", "missing", n=10)
