from pathlib import Path

import pandas as pd
import pytest

from toxicity_analysis.constants import TOLDBR_LABELS, TOLDBR_TEXT_COL

DATA = Path(__file__).resolve().parents[1] / "data" / "raw" / "told-br" / "train.csv"


pytestmark = pytest.mark.skipif(
    not DATA.exists(),
    reason="ToLD-Br not downloaded — see README for one-liner.",
)


@pytest.fixture(scope="module")
def told_br() -> pd.DataFrame:
    return pd.read_csv(DATA)


def test_shape(told_br: pd.DataFrame):
    assert told_br.shape == (21_000, 7)


def test_expected_columns(told_br: pd.DataFrame):
    assert set(told_br.columns) == {TOLDBR_TEXT_COL, *TOLDBR_LABELS}


def test_no_missing_values(told_br: pd.DataFrame):
    assert told_br.isna().sum().sum() == 0


def test_vote_counts_in_zero_to_three(told_br: pd.DataFrame):
    for label in TOLDBR_LABELS:
        assert told_br[label].between(0, 3).all(), f"{label} out of [0, 3]"
