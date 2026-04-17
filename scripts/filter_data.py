#!/usr/bin/env python3
"""
Filter raw news transcripts for articles mentioning federal judges.

This is the preprocessing step before LLM analysis.

Usage:
    python filter_data.py --source cnn --raw-file data/cnn-8.csv.gz
    python filter_data.py --source cnn --raw-file data/cnn-8.csv.gz --sample 500
    python filter_data.py --source cnn --raw-file data/cnn-8.csv.gz --sample 500 --seed 42
"""

import argparse
import re

import pandas as pd
from tqdm.auto import tqdm

from config import DATA_DIR, DATA_SOURCES

FEDERAL_JUDGE_PATTERNS = [
    r"\b(Supreme Court\s+Justice(s)?)\b",
    r"\b(Supreme Court\s+Judge(s)?)\b",
    r"\b(Circuit Court\s+Judge(s)?)\b",
    r"\b(Appellate Court\s+Judge(s)?)\b",
    r"\b(Federal\s+Appellate\s+Judge(s)?)\b",
    r"\b(District Court\s+Judge(s)?)\b",
    r"\b(Federal\s+District\s+Judge(s)?)\b",
    r"\b(Court of International Trade\s+Judge(s)?)\b",
    r"\b(Court of Federal Claims\s+Judge(s)?)\b",
    r"\b(Bankruptcy\s+Judge(s)?)\b",
    r"\b(Magistrate\s+Judge(s)?)\b",
]

DEFAULT_SAMPLE_SIZE = 500
DEFAULT_SEED = 42


def filter_federal_judge_articles(df: pd.DataFrame, text_column: str = "text") -> pd.DataFrame:
    """Filter articles mentioning federal judges."""
    compiled_patterns = [re.compile(p, re.IGNORECASE) for p in FEDERAL_JUDGE_PATTERNS]

    def has_federal_judge_mention(text: str) -> bool:
        if not isinstance(text, str):
            return False
        return any(p.search(text) for p in compiled_patterns)

    print("Filtering for federal judge mentions...")
    tqdm.pandas(desc="Scanning articles")
    mask = df[text_column].progress_apply(has_federal_judge_mention)
    return pd.DataFrame(df[mask].copy())


def main() -> None:
    parser = argparse.ArgumentParser(description="Filter transcripts for federal judge mentions")
    parser.add_argument("--source", choices=["cnn", "fox", "msnbc", "nbc"], default="cnn")
    parser.add_argument("--raw-file", type=str, help="Path to raw data file")
    parser.add_argument("--sample", type=int, default=None,
                        help=f"Sample N articles after filtering (default: no sampling)")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED,
                        help=f"Random seed for sampling (default: {DEFAULT_SEED})")
    args = parser.parse_args()

    source_config = DATA_SOURCES[args.source]

    if args.raw_file:
        raw_file = args.raw_file
    else:
        raw_files = source_config.get("raw_files", [source_config.get("raw_file", "")])
        raw_file = DATA_DIR / raw_files[0] if raw_files else None

    if not raw_file:
        print(f"No raw file specified. Download from: {source_config['dataverse_url']}")
        return

    print(f"Loading {raw_file}...")
    df = pd.read_csv(raw_file, compression="gzip")
    print(f"Loaded {len(df):,} articles")

    filtered_df = filter_federal_judge_articles(df)
    print(f"Found {len(filtered_df):,} articles mentioning federal judges ({100*len(filtered_df)/len(df):.1f}%)")

    if args.sample and args.sample < len(filtered_df):
        filtered_df = filtered_df.sample(n=args.sample, random_state=args.seed)
        print(f"Sampled {args.sample} articles (seed={args.seed})")

    output_file = DATA_DIR / f"{args.source}_judicial_articles.csv"
    filtered_df.to_csv(output_file, index=False)
    print(f"Saved to {output_file}")


if __name__ == "__main__":
    main()
