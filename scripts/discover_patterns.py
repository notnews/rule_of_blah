#!/usr/bin/env python3
"""
Discover patterns in transcripts to improve regex filtering.

Samples transcripts and extracts potential judicial terms to help
identify what patterns the current regex might be missing.

Usage:
    python discover_patterns.py --raw-file data/cnn-8.csv.gz --sample 1000
"""

import argparse
import re
from collections import Counter

import pandas as pd

# Known judicial terms to look for
JUDICIAL_TERMS = [
    # Courts
    r"\bSupreme Court\b",
    r"\bSCOTUS\b",
    r"\bCircuit Court\b",
    r"\bAppeals Court\b",
    r"\bCourt of Appeals\b",
    r"\bDistrict Court\b",
    r"\bFederal Court\b",
    r"\bAppellate\b",
    # Titles
    r"\bJustice\s+\w+\b",
    r"\bChief Justice\b",
    r"\bJudge\s+\w+\b",
    # Actions
    r"\bruled\b",
    r"\bruling\b",
    r"\bdecision\b",
    r"\bdecided\b",
    r"\bstruck down\b",
    r"\bupheld\b",
    r"\boverturned\b",
    # Named justices (current + recent)
    r"\bRoberts\b",
    r"\bThomas\b",
    r"\bAlito\b",
    r"\bSotomayor\b",
    r"\bKagan\b",
    r"\bGorsuch\b",
    r"\bKavanaugh\b",
    r"\bBarrett\b",
    r"\bJackson\b",
    r"\bGinsburg\b",
    r"\bScalia\b",
    r"\bKennedy\b",
    r"\bBreyer\b",
]


def analyze_patterns(df: pd.DataFrame, text_column: str = "text") -> dict:
    """Analyze frequency of judicial terms in transcripts."""
    compiled = [(term, re.compile(term, re.IGNORECASE)) for term in JUDICIAL_TERMS]

    counts: Counter = Counter()
    articles_with_term: Counter = Counter()

    for text in df[text_column].dropna():
        text = str(text)
        for term, pattern in compiled:
            matches = pattern.findall(text)
            if matches:
                counts[term] += len(matches)
                articles_with_term[term] += 1

    return {
        "total_matches": counts,
        "articles_with_term": articles_with_term,
        "total_articles": len(df),
    }


def find_justice_mentions(df: pd.DataFrame, text_column: str = "text") -> Counter:
    """Find mentions of 'Justice X' pattern to discover justice names."""
    pattern = re.compile(r"\bJustice\s+([A-Z][a-z]+)\b")
    names: Counter = Counter()

    for text in df[text_column].dropna():
        matches = pattern.findall(str(text))
        names.update(matches)

    return names


def find_judge_mentions(df: pd.DataFrame, text_column: str = "text") -> Counter:
    """Find mentions of 'Judge X' pattern to discover judge names."""
    pattern = re.compile(r"\bJudge\s+([A-Z][a-z]+)\b")
    names: Counter = Counter()

    for text in df[text_column].dropna():
        matches = pattern.findall(str(text))
        names.update(matches)

    return names


def main() -> None:
    parser = argparse.ArgumentParser(description="Discover judicial patterns in transcripts")
    parser.add_argument("--raw-file", type=str, required=True, help="Path to raw data file")
    parser.add_argument("--sample", type=int, default=1000, help="Sample size")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()

    print(f"Loading {args.raw_file}...")
    df = pd.read_csv(args.raw_file, compression="gzip")
    print(f"Loaded {len(df):,} articles")

    if args.sample < len(df):
        df = df.sample(n=args.sample, random_state=args.seed)
        print(f"Sampled {args.sample} articles")

    print("\n" + "=" * 60)
    print("JUDICIAL TERM FREQUENCY")
    print("=" * 60)

    results = analyze_patterns(df)

    print(f"\nArticles analyzed: {results['total_articles']}")
    print("\nTop terms by article count:")
    for term, count in results["articles_with_term"].most_common(20):
        pct = 100 * count / results["total_articles"]
        print(f"  {term:30s} {count:5d} articles ({pct:5.1f}%)")

    print("\n" + "=" * 60)
    print("JUSTICE NAMES (from 'Justice X' pattern)")
    print("=" * 60)
    justice_names = find_justice_mentions(df)
    for name, count in justice_names.most_common(15):
        print(f"  Justice {name:20s} {count:5d}")

    print("\n" + "=" * 60)
    print("JUDGE NAMES (from 'Judge X' pattern)")
    print("=" * 60)
    judge_names = find_judge_mentions(df)
    for name, count in judge_names.most_common(15):
        print(f"  Judge {name:20s} {count:5d}")


if __name__ == "__main__":
    main()
