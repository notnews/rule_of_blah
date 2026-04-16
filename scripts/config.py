"""Shared configuration for judicial coverage analysis."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
RESULTS_DIR = PROJECT_ROOT / "results"
DATA_DIR = PROJECT_ROOT / "data"
RESULTS_DIR.mkdir(exist_ok=True)

MODEL = "claude-sonnet-4-20250514"
MAX_BATCH_SIZE = 10000

DATA_SOURCES = {
    "cnn": {
        "judicial_file": "judicial_articles.csv",
        "raw_files": [f"cnn-{i}.csv.gz" for i in range(1, 9)],
        "dataverse_url": "http://dx.doi.org/10.7910/DVN/ISDPJU",
    },
    "fox": {
        "raw_file": "fox_news_transcripts.csv.gz",
        "dataverse_url": "https://dataverse.harvard.edu/dataset.xhtml?persistentId=doi:10.7910/DVN/Q2KIES",
    },
    "msnbc": {
        "raw_file": "msnbc_transcripts.csv.gz",
        "dataverse_url": "https://dataverse.harvard.edu/dataset.xhtml?persistentId=doi:10.7910/DVN/UPJDE1",
    },
    "nbc": {
        "raw_file": "nbc_transcripts.csv.gz",
        "dataverse_url": "http://dx.doi.org/10.7910/DVN/ND1TCV",
    },
}


def normalize_text(text: str) -> str:
    """Normalize text by collapsing whitespace and lowercasing."""
    return " ".join(text.lower().split())


def verify_quote(quote: str, text: str) -> bool:
    """Check if quote exists in article text (whitespace-normalized)."""
    if not quote or not text:
        return False
    return normalize_text(quote) in normalize_text(str(text))
