"""Dataset-level constants shared across modules and tests."""

TOLDBR_LABELS: tuple[str, ...] = (
    "homophobia",
    "obscene",
    "insult",
    "racism",
    "misogyny",
    "xenophobia",
)

TOLDBR_TEXT_COL: str = "text"

TOLDBR_MAJORITY_THRESHOLD: int = 2
