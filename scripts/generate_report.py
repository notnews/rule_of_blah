#!/usr/bin/env python3
"""Generate HTML report for judicial appointment analysis."""

import json
import webbrowser
from collections import defaultdict

import pandas as pd

from config import DATA_DIR, RESULTS_DIR, verify_quote

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Judicial Appointment Mentions in CNN Coverage</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        h1 {{ color: #1a1a2e; margin-bottom: 10px; }}
        h2 {{ color: #16213e; margin: 30px 0 15px; border-bottom: 2px solid #e94560; padding-bottom: 5px; }}
        h3 {{ color: #0f3460; margin: 20px 0 10px; }}
        .subtitle {{ color: #666; margin-bottom: 30px; }}

        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        .stat-card {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            text-align: center;
        }}
        .stat-number {{
            font-size: 2.5em;
            font-weight: bold;
            color: #e94560;
        }}
        .stat-label {{ color: #666; font-size: 0.9em; }}
        .stat-sublabel {{ color: #999; font-size: 0.8em; }}

        .bar-chart {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            margin: 20px 0;
        }}
        .bar {{
            display: flex;
            align-items: center;
            margin: 10px 0;
        }}
        .bar-label {{
            width: 120px;
            font-weight: 500;
        }}
        .bar-fill {{
            height: 25px;
            background: linear-gradient(90deg, #e94560, #0f3460);
            border-radius: 5px;
            display: flex;
            align-items: center;
            padding-left: 10px;
            color: white;
            font-size: 0.85em;
        }}

        .quotes-section {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            margin: 20px 0;
        }}
        .quote-card {{
            border-left: 4px solid #e94560;
            padding: 15px 20px;
            margin: 15px 0;
            background: #fafafa;
            border-radius: 0 8px 8px 0;
        }}
        .quote-card.president {{ border-left-color: #28a745; }}
        .quote-card.ideological {{ border-left-color: #ffc107; }}
        .quote-card.party {{ border-left-color: #17a2b8; }}

        .quote-text {{
            font-style: italic;
            font-size: 1.1em;
            color: #333;
            margin-bottom: 10px;
        }}
        .quote-meta {{
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }}
        .badge {{
            padding: 3px 10px;
            border-radius: 15px;
            font-size: 0.8em;
            font-weight: 500;
        }}
        .badge-president {{ background: #d4edda; color: #155724; }}
        .badge-ideological {{ background: #fff3cd; color: #856404; }}
        .badge-party {{ background: #d1ecf1; color: #0c5460; }}
        .badge-president {{ background: #e2e3e5; color: #383d41; }}
        .badge-verified {{ background: #cce5ff; color: #004085; }}
        .badge-unverified {{ background: #f8d7da; color: #721c24; }}

        .cases-list {{
            background: white;
            padding: 20px;
            border-radius: 10px;
        }}
        .case-item {{
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid #eee;
        }}
        .case-name {{ font-weight: 500; }}
        .case-count {{ color: #e94560; font-weight: bold; }}

        .methodology {{
            background: #f0f0f0;
            padding: 20px;
            border-radius: 10px;
            margin-top: 30px;
            font-size: 0.9em;
            color: #666;
        }}
        .methodology h3 {{ color: #333; }}
    </style>
</head>
<body>
    <h1>Judicial Appointment Mentions in CNN Coverage</h1>
    <p class="subtitle">LLM Analysis of {total:,} CNN Transcripts (2022-2025)</p>

    <h2>Summary Statistics</h2>
    <div class="stats-grid">
        <div class="stat-card">
            <div class="stat-number">{total:,}</div>
            <div class="stat-label">Judicial Articles</div>
            <div class="stat-sublabel">Filtered for court mentions</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">{num_decisions:,}</div>
            <div class="stat-label">Cover Decisions</div>
            <div class="stat-sublabel">{pct_decisions:.1f}% of articles</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">{num_mentions:,}</div>
            <div class="stat-label">Mention Appointments</div>
            <div class="stat-sublabel">{pct_mentions:.1f}% of decision articles</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">{total_mentions:,}</div>
            <div class="stat-label">Total Mentions</div>
            <div class="stat-sublabel">Across all articles</div>
        </div>
    </div>

    <h2>Decision Types</h2>
    <div class="bar-chart">
        <div class="bar">
            <span class="bar-label">Supreme Court</span>
            <div class="bar-fill" style="width: {pct_sc}%">{sc} ({pct_sc:.1f}%)</div>
        </div>
        <div class="bar">
            <span class="bar-label">Circuit Court</span>
            <div class="bar-fill" style="width: {pct_cc}%">{cc} ({pct_cc:.1f}%)</div>
        </div>
    </div>

    <h2>Mention Types</h2>
    <div class="bar-chart">
        <div class="bar">
            <span class="bar-label">President</span>
            <div class="bar-fill" style="width: {pct_president}%">{president_count} ({pct_president:.1f}%)</div>
        </div>
        <div class="bar">
            <span class="bar-label">Party</span>
            <div class="bar-fill" style="width: {pct_party}%">{party} ({pct_party:.1f}%)</div>
        </div>
        <div class="bar">
            <span class="bar-label">Ideological</span>
            <div class="bar-fill" style="width: {pct_ideological}%">{ideological} ({pct_ideological:.1f}%)</div>
        </div>
    </div>

    <h2>President Mentions</h2>
    <div class="bar-chart">
{president_bars}
    </div>

    <h2>All Quotes ({quote_count} total)</h2>
    <div class="quotes-section">
{quote_cards}
    </div>

    <h2>Top Cases Covered</h2>
    <div class="cases-list">
{case_items}
    </div>

    <div class="methodology">
        <h3>Methodology</h3>
        <p><strong>Stage 1 - Decision Detection:</strong> LLM analyzed each article to determine if it covers an actual Supreme Court or federal circuit court decision (ruling, judgment, opinion).</p>
        <p><strong>Stage 2 - Appointment Detection:</strong> For articles covering decisions, LLM identified all mentions of who appointed judges, including:</p>
        <ul>
            <li><strong>Explicit:</strong> "appointed by President Trump", "Biden nominee"</li>
            <li><strong>Implicit:</strong> "conservative majority", "Trump-era court"</li>
            <li><strong>Party-based:</strong> "GOP-appointed judges", "Republican nominees"</li>
        </ul>
        <p><strong>Quote Verification:</strong> {verified_count}/{quote_count} sample quotes verified against source text ({verification_pct:.0f}%)</p>
        <p><strong>Model:</strong> Claude Sonnet (claude-sonnet-4-20250514) via Anthropic Batch API</p>
    </div>
</body>
</html>
"""


def load_data() -> tuple[list, list, dict]:
    """Load analysis results and article data."""
    with open(RESULTS_DIR / "cnn_stage1_results.json") as f:
        stage1 = json.load(f)

    with open(RESULTS_DIR / "cnn_stage2_results.json") as f:
        stage2 = json.load(f)

    df = pd.read_csv(DATA_DIR / "judicial_articles.csv")
    articles = {f"row_{i}": row for i, row in df.iterrows()}

    return stage1, stage2, articles


def collect_all_quotes(stage2: list, articles: dict) -> list[dict]:
    """Collect all quotes with verification for audit."""
    all_quotes = []
    for r in stage2:
        uid = r.get("uid")
        article = articles.get(uid, {})
        text = str(article.get("text", ""))

        year = article.get("year")
        month = article.get("month")
        day = article.get("date")
        if year and month and day:
            date_str = f"{int(year)}-{int(month):02d}-{int(day):02d}"
        else:
            date_str = ""

        for m in r.get("mentions", []):
            quote = m.get("quote", "")
            if quote:
                all_quotes.append(
                    {
                        "uid": uid,
                        "url": article.get("url", ""),
                        "date": date_str,
                        "program": article.get("program.name", ""),
                        "quote": quote,
                        "type": m.get("type", "unknown"),
                        "president": m.get("president", "unknown"),
                        "judge": m.get("judge_name"),
                        "context": m.get("context", ""),
                        "verified": verify_quote(quote, text),
                    }
                )
    return all_quotes


def generate_html(stage1: list, stage2: list, articles: dict) -> str:
    """Generate HTML report."""
    total = len(stage1)
    decisions = [r for r in stage1 if r.get("covers_court_decision")]
    mentions_articles = [r for r in stage2 if r.get("has_appointment_mentions")]

    sc = sum(1 for r in decisions if r.get("decision_type") == "supreme_court")
    cc = sum(1 for r in decisions if r.get("decision_type") == "circuit_court")

    president_count = sum(r.get("president_mentions", 0) for r in stage2)
    party = sum(r.get("party_mentions", 0) for r in stage2)
    ideological = sum(r.get("ideological_mentions", 0) for r in stage2)
    total_mentions = president_count + party + ideological

    presidents: dict[str, int] = defaultdict(int)
    for r in stage2:
        for m in r.get("mentions", []):
            presidents[m.get("president", "unknown")] += 1

    cases: dict[str, int] = defaultdict(int)
    for r in stage1:
        if r.get("case_name"):
            cases[r["case_name"]] += 1

    all_quotes = collect_all_quotes(stage2, articles)

    sorted_pres = sorted(presidents.items(), key=lambda x: -x[1])
    max_count = sorted_pres[0][1] if sorted_pres else 1
    president_bars = ""
    for pres, count in sorted_pres[:7]:
        pct = 100 * count / total_mentions
        width = 100 * count / max_count
        president_bars += f"""        <div class="bar">
            <span class="bar-label">{pres}</span>
            <div class="bar-fill" style="width: {width}%">{count} ({pct:.1f}%)</div>
        </div>
"""

    quote_cards = ""
    for q in all_quotes:
        verified_badge = "badge-verified" if q["verified"] else "badge-unverified"
        verified_text = "Verified" if q["verified"] else "Unverified"
        judge_badge = (
            f'<span class="badge" style="background:#e0e0e0">Judge: {q["judge"]}</span>'
            if q["judge"]
            else ""
        )
        date_badge = (
            f'<span class="badge" style="background:#f0f0f0">{q["date"]}</span>'
            if q["date"]
            else ""
        )
        program_badge = (
            f'<span class="badge" style="background:#e8f4f8">{q["program"]}</span>'
            if q["program"]
            else ""
        )
        url_link = (
            f'<a href="{q["url"]}" target="_blank" style="font-size:0.8em;color:#0066cc;">Transcript</a>'
            if q["url"]
            else ""
        )

        quote_cards += f"""        <div class="quote-card {q["type"]}">
            <div class="quote-text">"{q["quote"]}"</div>
            <div class="quote-meta">
                <span class="badge badge-{q["type"]}">{q["type"].capitalize()}</span>
                <span class="badge badge-president">{q["president"]}</span>
                <span class="badge {verified_badge}">{verified_text}</span>
                {judge_badge}
                {date_badge}
                {program_badge}
                {url_link}
            </div>
        </div>
"""

    case_items = ""
    for case, count in sorted(cases.items(), key=lambda x: -x[1])[:10]:
        case_items += f"""        <div class="case-item">
            <span class="case-name">{case}</span>
            <span class="case-count">{count} articles</span>
        </div>
"""

    verified_count = sum(1 for q in all_quotes if q["verified"])

    return HTML_TEMPLATE.format(
        total=total,
        num_decisions=len(decisions),
        pct_decisions=100 * len(decisions) / total,
        num_mentions=len(mentions_articles),
        pct_mentions=100 * len(mentions_articles) / len(decisions),
        total_mentions=total_mentions,
        sc=sc,
        pct_sc=100 * sc / len(decisions),
        cc=cc,
        pct_cc=100 * cc / len(decisions),
        president_count=president_count,
        pct_president=100 * president_count / total_mentions,
        ideological=ideological,
        pct_ideological=100 * ideological / total_mentions,
        party=party,
        pct_party=100 * party / total_mentions,
        president_bars=president_bars,
        quote_cards=quote_cards,
        case_items=case_items,
        verified_count=verified_count,
        quote_count=len(all_quotes),
        verification_pct=100 * verified_count / len(all_quotes) if all_quotes else 0,
    )


def main() -> None:
    print("Loading data...")
    stage1, stage2, articles = load_data()

    print("Generating HTML report...")
    html = generate_html(stage1, stage2, articles)

    output_file = RESULTS_DIR / "cnn_report.html"
    with open(output_file, "w") as f:
        f.write(html)

    print(f"Report saved to {output_file}")
    print("Opening in browser...")
    webbrowser.open(f"file://{output_file.absolute()}")


if __name__ == "__main__":
    main()
