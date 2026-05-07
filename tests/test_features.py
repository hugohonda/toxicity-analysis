import numpy as np
import pandas as pd
import pytest

from toxicity_analysis.features import (
    add_lexical_features,
    feature_summary,
    vote_noise_breakdown,
)


class TestAddLexicalFeatures:
    def test_columns_added(self):
        df = pd.DataFrame({"text": ["hello world", "FOO BAR baz"]})
        out = add_lexical_features(df)
        for col in ["word_count", "unique_word_ratio", "caps_ratio",
                    "punc_density", "mean_word_length"]:
            assert col in out.columns

    def test_input_not_mutated(self):
        df = pd.DataFrame({"text": ["hi"]})
        original_cols = list(df.columns)
        add_lexical_features(df)
        assert list(df.columns) == original_cols

    def test_word_count_simple(self):
        df = pd.DataFrame({"text": ["one two three", "", "single"]})
        out = add_lexical_features(df)
        assert list(out["word_count"]) == [3, 0, 1]

    def test_caps_ratio_extremes(self):
        df = pd.DataFrame({"text": ["lowercase", "UPPERCASE", "MiXeD", "12345"]})
        out = add_lexical_features(df)
        assert out["caps_ratio"].iloc[0] == 0.0
        assert out["caps_ratio"].iloc[1] == 1.0
        assert out["caps_ratio"].iloc[2] == pytest.approx(3 / 5)
        assert out["caps_ratio"].iloc[3] == 0.0

    def test_unique_word_ratio_repetition(self):
        df = pd.DataFrame({"text": ["a a a a", "a b c d", ""]})
        out = add_lexical_features(df)
        assert out["unique_word_ratio"].iloc[0] == pytest.approx(0.25)
        assert out["unique_word_ratio"].iloc[1] == 1.0
        assert out["unique_word_ratio"].iloc[2] == 0.0

    def test_punc_density_handles_empty(self):
        df = pd.DataFrame({"text": ["", "!!!", "hello, world!"]})
        out = add_lexical_features(df)
        assert out["punc_density"].iloc[0] == 0.0
        assert out["punc_density"].iloc[1] == 1.0
        assert 0 < out["punc_density"].iloc[2] < 1

    def test_mean_word_length_no_words(self):
        df = pd.DataFrame({"text": ["", "!!!"]})
        out = add_lexical_features(df)
        assert out["mean_word_length"].iloc[0] == 0.0
        assert out["mean_word_length"].iloc[1] == 0.0

    def test_missing_text_col_raises(self):
        df = pd.DataFrame({"comment": ["hi"]})
        with pytest.raises(KeyError):
            add_lexical_features(df, text_col="text")


class TestFeatureSummary:
    def test_ungrouped_returns_mean_sem_n(self):
        df = pd.DataFrame({"x": [1.0, 2.0, 3.0, 4.0]})
        out = feature_summary(df, ["x"])
        assert out.loc["x", "mean"] == 2.5
        assert out.loc["x", "n"] == 4
        assert out.loc["x", "sem"] == pytest.approx(np.std([1, 2, 3, 4], ddof=1) / 2)

    def test_grouped_summary(self):
        df = pd.DataFrame({"x": [1, 2, 10, 20], "g": ["a", "a", "b", "b"]})
        out = feature_summary(df, ["x"], group_col="g")
        assert out.loc["a", "x_mean"] == 1.5
        assert out.loc["b", "x_mean"] == 15.0
        assert out.loc["a", "n"] == 2
        assert out.loc["b", "n"] == 2


class TestVoteNoiseBreakdown:
    def test_synthetic_counts_match_inputs(self):
        df = pd.DataFrame({
            "racism":     [0, 0, 0, 1, 2, 3],
            "homophobia": [0, 1, 1, 2, 2, 3],
            "obscene":    [0, 0, 0, 0, 0, 0],
            "insult":     [0, 0, 0, 0, 0, 0],
            "misogyny":   [0, 0, 0, 0, 0, 0],
            "xenophobia": [0, 0, 0, 0, 0, 0],
        })
        out = vote_noise_breakdown(df)
        assert out.loc["racism", "votes_0"] == 3
        assert out.loc["racism", "votes_1"] == 1
        assert out.loc["racism", "votes_2"] == 1
        assert out.loc["racism", "votes_3"] == 1
        assert out.loc["racism", "positives_majority"] == 2  # votes >= 2
        assert out.loc["racism", "disputed_share"] == pytest.approx(1 / 6)

    def test_all_zero_label(self):
        df = pd.DataFrame({label: [0] * 100 for label in [
            "homophobia", "obscene", "insult", "racism", "misogyny", "xenophobia",
        ]})
        out = vote_noise_breakdown(df)
        assert out["positives_majority"].sum() == 0
        assert out["disputed_share"].sum() == 0

    def test_threshold_change_increases_positives(self):
        df = pd.DataFrame({label: [1] * 100 for label in [
            "homophobia", "obscene", "insult", "racism", "misogyny", "xenophobia",
        ]})
        strict = vote_noise_breakdown(df, threshold=2)
        loose = vote_noise_breakdown(df, threshold=1)
        assert (loose["positives_majority"] > strict["positives_majority"]).all()
