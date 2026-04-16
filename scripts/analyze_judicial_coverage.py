#!/usr/bin/env python3
"""
Analyze judicial coverage in news transcripts using LLM Batch API.

Two-stage pipeline:
1. Decision Detection: Filter articles that cover actual court decisions
2. Appointment Mention Detection: Find all mentions of who appointed judges

Uses Anthropic's Message Batches API for 50% cost reduction.
Batches process within 24 hours (often much faster).

Usage:
    python analyze_judicial_coverage.py --pilot 5  # Run pilot (sync mode)
    python analyze_judicial_coverage.py --batch-submit --source cnn  # Submit batch
    python analyze_judicial_coverage.py --batch-status BATCH_ID  # Check status
    python analyze_judicial_coverage.py --batch-retrieve BATCH_ID  # Get results
"""

import argparse
import json
import os
import re

import anthropic
import pandas as pd
from tqdm.auto import tqdm

from config import DATA_DIR, DATA_SOURCES, MAX_BATCH_SIZE, MODEL, RESULTS_DIR, verify_quote
from prompts import APPOINTMENT_DETECTION_PROMPT, DECISION_DETECTION_PROMPT


def get_client() -> anthropic.Anthropic:
    """Get Anthropic client."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable not set")
    return anthropic.Anthropic(api_key=api_key)


def load_judicial_articles(source: str = "cnn") -> pd.DataFrame:
    """Load pre-filtered judicial articles or filter from raw data."""
    if source == "cnn":
        judicial_file = DATA_DIR / "judicial_articles.csv"
        if judicial_file.exists():
            print(f"Loading pre-filtered judicial articles from {judicial_file}")
            return pd.read_csv(judicial_file)

    raw_file = DATA_DIR / DATA_SOURCES[source].get("raw_file", "")
    if raw_file.exists():
        print(f"Loading raw data from {raw_file} and filtering...")
        df = pd.read_csv(raw_file, compression="gzip")
        return filter_federal_judge_articles(df)

    raise FileNotFoundError(
        f"Data not found for {source}. Download from: {DATA_SOURCES[source]['dataverse_url']}"
    )


def filter_federal_judge_articles(df: pd.DataFrame, text_column: str = "text") -> pd.DataFrame:
    """Filter articles mentioning federal judges."""
    federal_judge_patterns = [
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

    compiled_patterns = [re.compile(p, re.IGNORECASE) for p in federal_judge_patterns]

    def has_federal_judge_mention(text: str) -> bool:
        if not isinstance(text, str):
            return False
        return any(p.search(text) for p in compiled_patterns)

    mask = df[text_column].apply(has_federal_judge_mention)
    return pd.DataFrame(df[mask].copy())


def truncate_text(text: str, max_chars: int = 100000) -> str:
    """Truncate text to fit within token limits."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n[... text truncated ...]"


def parse_llm_response(content: str) -> dict:
    """Parse JSON from LLM response."""
    json_match = re.search(r"\{[\s\S]*\}", content)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            return {"error": "Failed to parse JSON", "raw_response": content}
    return {"error": "No JSON found in response", "raw_response": content}


def call_llm(client: anthropic.Anthropic, prompt: str, text: str) -> dict:
    """Call LLM with prompt and text, return parsed JSON response."""
    formatted_prompt = prompt.format(text=truncate_text(text))

    response = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        messages=[{"role": "user", "content": formatted_prompt}],
    )

    content = response.content[0].text
    return parse_llm_response(content)


def verify_mentions(text: str, mentions: list[dict]) -> list[dict]:
    """Verify that quotes actually appear in the article text."""
    for mention in mentions:
        quote = mention.get("quote", "")
        mention["quote_verified"] = verify_quote(quote, text)
        if not mention["quote_verified"]:
            mention["verification_note"] = "Quote not found in article"
    return mentions


def create_batch_requests(
    df: pd.DataFrame,
    stage: int,
    decision_results: dict | None = None,
) -> list[dict]:
    """Create batch request objects for the Anthropic Batch API."""
    requests = []

    for idx, row in df.iterrows():
        uid = f"row_{idx}"
        text = str(row.get("text", ""))

        if stage == 1:
            prompt = DECISION_DETECTION_PROMPT.format(text=truncate_text(text))
            custom_id = f"stage1_{uid}"
        elif stage == 2:
            if decision_results and uid not in decision_results:
                continue
            if decision_results and not decision_results[uid].get("covers_court_decision", False):
                continue
            prompt = APPOINTMENT_DETECTION_PROMPT.format(text=truncate_text(text))
            custom_id = f"stage2_{uid}"
        else:
            raise ValueError(f"Invalid stage: {stage}")

        requests.append({
            "custom_id": custom_id,
            "params": {
                "model": MODEL,
                "max_tokens": 2000,
                "messages": [{"role": "user", "content": prompt}],
            },
        })

    return requests


def submit_batch(
    source: str = "cnn",
    stage: int = 1,
    limit: int | None = None,
    decision_results_file: str | None = None,
) -> str:
    """Submit a batch job and return the batch ID."""
    print(f"\n{'='*60}")
    print(f"BATCH SUBMISSION: {source.upper()} - Stage {stage}")
    print(f"{'='*60}\n")

    client = get_client()
    df = load_judicial_articles(source)

    if limit:
        df = df.head(limit)

    decision_results = None
    if stage == 2 and decision_results_file:
        with open(decision_results_file) as f:
            stage1_data = json.load(f)
            decision_results = {r["uid"]: r for r in stage1_data}
        print(f"Loaded {len(decision_results)} stage 1 results")

    requests = create_batch_requests(df, stage, decision_results)
    print(f"Created {len(requests)} batch requests")

    if len(requests) == 0:
        print("No requests to submit")
        return ""

    if len(requests) > MAX_BATCH_SIZE:
        print(f"Warning: {len(requests)} requests exceeds max batch size of {MAX_BATCH_SIZE}")
        print(f"Submitting first {MAX_BATCH_SIZE} requests")
        requests = requests[:MAX_BATCH_SIZE]

    batch = client.messages.batches.create(requests=requests)

    batch_info = {
        "batch_id": batch.id,
        "source": source,
        "stage": stage,
        "num_requests": len(requests),
        "created_at": str(batch.created_at),
        "processing_status": batch.processing_status,
    }

    batch_file = RESULTS_DIR / f"batch_{source}_stage{stage}_{batch.id}.json"
    with open(batch_file, "w") as f:
        json.dump(batch_info, f, indent=2)

    print(f"\nBatch submitted successfully!")
    print(f"Batch ID: {batch.id}")
    print(f"Status: {batch.processing_status}")
    print(f"Batch info saved to: {batch_file}")

    return batch.id


def check_batch_status(batch_id: str) -> dict:
    """Check the status of a batch job."""
    client = get_client()
    batch = client.messages.batches.retrieve(batch_id)

    status = {
        "batch_id": batch.id,
        "processing_status": batch.processing_status,
        "created_at": str(batch.created_at),
        "ended_at": str(batch.ended_at) if batch.ended_at else None,
        "request_counts": {
            "processing": batch.request_counts.processing,
            "succeeded": batch.request_counts.succeeded,
            "errored": batch.request_counts.errored,
            "canceled": batch.request_counts.canceled,
            "expired": batch.request_counts.expired,
        },
    }

    print(f"\n{'='*60}")
    print(f"BATCH STATUS: {batch_id}")
    print(f"{'='*60}")
    print(f"Status: {status['processing_status']}")
    print(f"Created: {status['created_at']}")
    if status["ended_at"]:
        print(f"Ended: {status['ended_at']}")
    print(f"\nRequest counts:")
    for k, v in status["request_counts"].items():
        print(f"  {k}: {v}")

    return status


def retrieve_batch_results(
    batch_id: str,
    source: str = "cnn",
    stage: int = 1,
    articles_file: str | None = None,
) -> list:
    """Retrieve and process results from a completed batch."""
    client = get_client()

    batch = client.messages.batches.retrieve(batch_id)
    if batch.processing_status != "ended":
        print(f"Batch not complete. Status: {batch.processing_status}")
        return []

    print(f"\n{'='*60}")
    print(f"RETRIEVING BATCH RESULTS: {batch_id}")
    print(f"{'='*60}\n")

    articles_map = {}
    if articles_file:
        df = pd.read_csv(articles_file)
        articles_map = {str(row["uid"]): row.to_dict() for _, row in df.iterrows()}

    results = []
    for result in client.messages.batches.results(batch_id):
        custom_id = result.custom_id
        uid = custom_id.split("_", 1)[1] if "_" in custom_id else custom_id

        if result.result.type == "succeeded":
            content = result.result.message.content[0].text
            parsed = parse_llm_response(content)
        else:
            parsed = {"error": f"Request failed: {result.result.type}"}

        article_info = articles_map.get(uid, {})

        if stage == 1:
            record = {
                "uid": uid,
                "source": article_info.get("channel.name", source),
                "date": article_info.get("date", ""),
                "year": article_info.get("year", ""),
                "program": article_info.get("program.name", ""),
                "covers_court_decision": parsed.get("covers_court_decision", False),
                "decision_type": parsed.get("decision_type"),
                "case_name": parsed.get("case_name"),
                "decision_evidence": parsed.get("evidence_quotes", []),
                "decision_summary": parsed.get("brief_summary"),
            }
            if parsed.get("error"):
                record["stage1_error"] = parsed["error"]
        else:
            text = article_info.get("text", "")
            mentions = parsed.get("mentions", [])
            if text and mentions:
                mentions = verify_mentions(text, mentions)

            record = {
                "uid": uid,
                "has_appointment_mentions": parsed.get("has_appointment_mentions", False),
                "mentions": mentions,
                "total_mentions": len(mentions),
                "explicit_mentions": parsed.get("total_explicit_mentions", 0),
                "implicit_mentions": parsed.get("total_implicit_mentions", 0),
                "party_mentions": parsed.get("total_party_mentions", 0),
            }
            if parsed.get("error"):
                record["stage2_error"] = parsed["error"]

        results.append(record)

    output_file = RESULTS_DIR / f"{source}_stage{stage}_results.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)

    print(f"Retrieved {len(results)} results")
    print(f"Saved to: {output_file}")

    if stage == 1:
        summarize_stage1_results(results, source)

    return results


def merge_results(source: str = "cnn") -> list:
    """Merge stage 1 and stage 2 results into final output."""
    stage1_file = RESULTS_DIR / f"{source}_stage1_results.json"
    stage2_file = RESULTS_DIR / f"{source}_stage2_results.json"

    if not stage1_file.exists():
        raise FileNotFoundError(f"Stage 1 results not found: {stage1_file}")

    with open(stage1_file) as f:
        stage1_results = json.load(f)

    stage2_map = {}
    if stage2_file.exists():
        with open(stage2_file) as f:
            stage2_results = json.load(f)
            stage2_map = {r["uid"]: r for r in stage2_results}

    final_results = []
    for r1 in stage1_results:
        uid = r1["uid"]
        merged = r1.copy()

        if uid in stage2_map:
            r2 = stage2_map[uid]
            merged.update({
                "has_appointment_mentions": r2.get("has_appointment_mentions", False),
                "mentions": r2.get("mentions", []),
                "total_mentions": r2.get("total_mentions", 0),
                "explicit_mentions": r2.get("explicit_mentions", 0),
                "implicit_mentions": r2.get("implicit_mentions", 0),
                "party_mentions": r2.get("party_mentions", 0),
            })
            if r2.get("stage2_error"):
                merged["stage2_error"] = r2["stage2_error"]
        else:
            merged.update({
                "has_appointment_mentions": False,
                "mentions": [],
                "total_mentions": 0,
            })

        final_results.append(merged)

    output_file = RESULTS_DIR / f"{source}_final_results.json"
    with open(output_file, "w") as f:
        json.dump(final_results, f, indent=2)

    print(f"\n{'='*60}")
    print(f"MERGED RESULTS: {source.upper()}")
    print(f"{'='*60}")
    print(f"Total articles: {len(final_results)}")
    print(f"Saved to: {output_file}")

    summarize_results(final_results, source)

    return final_results


def summarize_stage1_results(results: list, source: str) -> None:
    """Print summary for stage 1 results."""
    total = len(results)
    covers_decision = sum(1 for r in results if r.get("covers_court_decision"))

    print(f"\n{'='*60}")
    print(f"STAGE 1 SUMMARY: {source.upper()}")
    print(f"{'='*60}")
    print(f"Total articles analyzed: {total}")
    print(f"Cover court decisions: {covers_decision} ({100*covers_decision/total:.1f}%)")

    if covers_decision > 0:
        decision_articles = [r for r in results if r.get("covers_court_decision")]
        sc_count = sum(1 for r in decision_articles if r.get("decision_type") == "supreme_court")
        cc_count = sum(1 for r in decision_articles if r.get("decision_type") == "circuit_court")
        both_count = sum(1 for r in decision_articles if r.get("decision_type") == "both")
        print(f"\nDecision types:")
        print(f"  Supreme Court: {sc_count}")
        print(f"  Circuit Court: {cc_count}")
        print(f"  Both: {both_count}")


def summarize_results(results: list, source: str) -> None:
    """Print summary statistics for final results."""
    total = len(results)
    covers_decision = sum(1 for r in results if r.get("covers_court_decision"))
    has_mentions = sum(1 for r in results if r.get("has_appointment_mentions"))

    print(f"\n{'='*60}")
    print(f"FINAL SUMMARY: {source.upper()}")
    print(f"{'='*60}")
    print(f"Total articles analyzed: {total}")
    print(f"Cover court decisions: {covers_decision} ({100*covers_decision/total:.1f}%)")
    if covers_decision > 0:
        print(f"Have appointment mentions: {has_mentions} ({100*has_mentions/covers_decision:.1f}% of decisions)")

    mention_articles = [r for r in results if r.get("has_appointment_mentions")]
    if mention_articles:
        explicit = sum(r.get("explicit_mentions", 0) for r in mention_articles)
        implicit = sum(r.get("implicit_mentions", 0) for r in mention_articles)
        party = sum(r.get("party_mentions", 0) for r in mention_articles)
        print(f"\nMention types across articles:")
        print(f"  Explicit: {explicit}")
        print(f"  Implicit: {implicit}")
        print(f"  Party-based: {party}")

        presidents: dict[str, int] = {}
        for r in mention_articles:
            for m in r.get("mentions", []):
                pres = m.get("president", "unknown")
                presidents[pres] = presidents.get(pres, 0) + 1
        if presidents:
            print(f"\nPresident mentions:")
            for pres, count in sorted(presidents.items(), key=lambda x: -x[1]):
                print(f"  {pres}: {count}")


def analyze_article(client: anthropic.Anthropic, article: dict) -> dict:
    """Run two-stage analysis on a single article (sync mode for pilot)."""
    text = article.get("text", "")
    uid = article.get("uid", "unknown")

    result: dict = {
        "uid": uid,
        "source": article.get("channel.name", "unknown"),
        "date": article.get("date", ""),
        "year": article.get("year", ""),
        "program": article.get("program.name", ""),
    }

    stage1 = call_llm(client, DECISION_DETECTION_PROMPT, text)
    result["covers_court_decision"] = stage1.get("covers_court_decision", False)
    result["decision_type"] = stage1.get("decision_type")
    result["case_name"] = stage1.get("case_name")
    result["decision_evidence"] = stage1.get("evidence_quotes", [])
    result["decision_summary"] = stage1.get("brief_summary")

    if stage1.get("error"):
        result["stage1_error"] = stage1.get("error")
        result["has_appointment_mentions"] = False
        result["mentions"] = []
        result["total_mentions"] = 0
        return result

    if not result["covers_court_decision"]:
        result["has_appointment_mentions"] = False
        result["mentions"] = []
        result["total_mentions"] = 0
        return result

    stage2 = call_llm(client, APPOINTMENT_DETECTION_PROMPT, text)

    if stage2.get("error"):
        result["stage2_error"] = stage2.get("error")
        result["has_appointment_mentions"] = False
        result["mentions"] = []
        result["total_mentions"] = 0
        return result

    mentions = stage2.get("mentions", [])
    verified_mentions = verify_mentions(text, mentions)

    result["has_appointment_mentions"] = stage2.get("has_appointment_mentions", False)
    result["mentions"] = verified_mentions
    result["total_mentions"] = len(verified_mentions)
    result["explicit_mentions"] = stage2.get("total_explicit_mentions", 0)
    result["implicit_mentions"] = stage2.get("total_implicit_mentions", 0)
    result["party_mentions"] = stage2.get("total_party_mentions", 0)

    return result


def run_pilot(n: int = 5) -> list:
    """Run pilot analysis on n articles with full output for validation."""
    print(f"\n{'='*60}")
    print(f"PILOT RUN (SYNC MODE): Analyzing {n} articles")
    print(f"{'='*60}\n")

    client = get_client()
    df = load_judicial_articles("cnn")

    sample = df.sample(n=min(n, len(df)), random_state=42)

    results = []
    for _, row in tqdm(sample.iterrows(), total=len(sample), desc="Analyzing"):
        article = row.to_dict()
        result = analyze_article(client, article)
        results.append(result)

        print(f"\n{'─'*60}")
        print(f"Article UID: {result['uid']}")
        print(f"Date: {result['date']}")
        print(f"Covers Decision: {result['covers_court_decision']}")
        if result["covers_court_decision"]:
            print(f"Decision Type: {result['decision_type']}")
            print(f"Case: {result.get('case_name', 'N/A')}")
            print(f"Has Appointment Mentions: {result['has_appointment_mentions']}")
            if result["has_appointment_mentions"]:
                print(f"Total Mentions: {result['total_mentions']}")
                for i, mention in enumerate(result["mentions"], 1):
                    verified = "+" if mention.get("quote_verified") else "-"
                    print(f"  {i}. [{verified}] {mention.get('type', 'unknown')}: {mention.get('quote', '')[:80]}...")
                    print(f"      President: {mention.get('president', 'unknown')}, Judge: {mention.get('judge_name', 'N/A')}")

    output_file = RESULTS_DIR / "pilot_results.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n\nPilot results saved to {output_file}")

    return results


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze judicial coverage in news transcripts (Batch API)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Workflow for batch processing:
  1. Submit stage 1 batch:
     python analyze_judicial_coverage.py --batch-submit --source cnn --stage 1

  2. Check status:
     python analyze_judicial_coverage.py --batch-status BATCH_ID

  3. Retrieve stage 1 results when complete:
     python analyze_judicial_coverage.py --batch-retrieve BATCH_ID --source cnn --stage 1 --articles judicial_articles.csv

  4. Submit stage 2 batch (only articles with decisions):
     python analyze_judicial_coverage.py --batch-submit --source cnn --stage 2 --decision-results results/cnn_stage1_results.json

  5. Retrieve stage 2 results and merge:
     python analyze_judicial_coverage.py --batch-retrieve BATCH_ID --source cnn --stage 2 --articles judicial_articles.csv
     python analyze_judicial_coverage.py --merge --source cnn
        """,
    )

    parser.add_argument("--pilot", type=int, help="Run pilot on N articles (sync mode)")
    parser.add_argument("--source", choices=["cnn", "fox", "msnbc", "nbc"], default="cnn")
    parser.add_argument("--limit", type=int, help="Limit number of articles")

    parser.add_argument("--batch-submit", action="store_true", help="Submit a batch job")
    parser.add_argument("--stage", type=int, choices=[1, 2], default=1, help="Pipeline stage")
    parser.add_argument("--decision-results", type=str, help="Stage 1 results file (for stage 2)")

    parser.add_argument("--batch-status", type=str, metavar="BATCH_ID", help="Check batch status")
    parser.add_argument("--batch-retrieve", type=str, metavar="BATCH_ID", help="Retrieve batch results")
    parser.add_argument("--articles", type=str, help="Articles CSV file for enrichment")

    parser.add_argument("--merge", action="store_true", help="Merge stage 1 and 2 results")

    args = parser.parse_args()

    if args.pilot:
        run_pilot(args.pilot)
    elif args.batch_submit:
        submit_batch(
            source=args.source,
            stage=args.stage,
            limit=args.limit,
            decision_results_file=args.decision_results,
        )
    elif args.batch_status:
        check_batch_status(args.batch_status)
    elif args.batch_retrieve:
        retrieve_batch_results(
            batch_id=args.batch_retrieve,
            source=args.source,
            stage=args.stage,
            articles_file=args.articles,
        )
    elif args.merge:
        merge_results(args.source)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
