## The Rule of Blah/Bench Marks

The classical rule of law demands that legal outcomes track declared rules rather than the political commitments of whoever happens to be on the bench. Dicey's 1885 formulation still does the work: "no man is punishable or can lawfully be made to suffer in body or goods except for a distinct breach of law established in the ordinary legal manner before the ordinary courts of the land." Neutrality and consistency are the ideal. When judges' votes correlate systematically with the party of the president who appointed them, the ideal erodes, and so does public confidence that like cases will be treated alike.

The empirical record leaves little room for the fiction that judging is pure law-application. Segal and Spaeth's attitudinal model shows that Supreme Court justices' votes track their pre-confirmation ideological scores closely enough to explain roughly two-thirds of the variance in civil-liberties cases. The pattern runs down the federal hierarchy. Studies of federal sentencing after *United States v. Booker* find that Republican-appointed district judges impose meaningfully longer sentences than Democratic-appointed peers, with larger gaps for Black defendants. Analyses of hundreds of thousands of circuit-court dispositions find that panels with more Republican appointees are less likely to rule for the weaker party in cases involving civil plaintiffs, immigrants, and workers. Judge fixed effects rule out court-level confounders. Two citizens with identical cases can reasonably expect different outcomes depending on who drew what judge.

Against that backdrop, how news outlets describe judges matters. A story that reports a ruling without noting the bench's partisan composition invites readers to treat the ruling as neutral legal output. A story that foregrounds who appointed whom invites the opposite reading, that courts are extensions of the political branches by other means. Both framings shape what a ruling is taken to mean, and neither is inert color commentary.

This project measures one slice of that framing. When a cable news segment covers an actual federal court decision, how often does the coverage mention who appointed the judges? When it does, is the appointment attributed to a specific president, to a party ("GOP-appointed"), or only indirectly through ideological labels like "the conservative majority"? The answers trace the implicit theory of judging that one outlet's coverage conveys, aggregated across thousands of segments.

## Key Findings (CNN 2022-2025)

| Metric | Value |
|--------|-------|
| Judicial articles analyzed | 2,542 |
| Articles covering court decisions | 565 (22%) |
| Decision articles mentioning appointments | 281 (50%) |
| Implicit mentions ("conservative majority") | 482 (55%) |
| Explicit mentions ("appointed by Trump") | 354 (40%) |
| Party-based mentions ("GOP-appointed") | 49 (5%) |
| Trump appointees mentioned | 379 (43% of all mentions) |
| Quote verification rate | 97% |

Roughly one in five judicial segments on CNN between 2022 and 2025 covered an actual ruling, and of those, half mentioned who appointed the judges. Implicit ideological framing ("conservative majority," "liberal justices") dominated over explicit presidential attribution, and explicit attribution dominated over party framing. Trump appointees accounted for 43 percent of all mentions, reflecting both the salience of the Dobbs-era court and the tendency of coverage to personalize the bench around the appointing president.

## Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│  STEP 0: FILTER DATA                          (filter_data.py)  │
│  Download transcripts from Dataverse → Filter for judge mentions│
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 1: DECISION DETECTION      (analyze_judicial_coverage.py) │
│  LLM classifies each article:                                   │
│  • Does it cover an actual court decision?                      │
│  • Supreme Court or Circuit Court?                              │
│  • What case?                                                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼ (only articles with decisions)
┌─────────────────────────────────────────────────────────────────┐
│  STEP 2: APPOINTMENT DETECTION   (analyze_judicial_coverage.py) │
│  LLM extracts all mentions of who appointed judges:             │
│  • Explicit: "appointed by President Trump"                     │
│  • Implicit: "conservative majority"                            │
│  • Party-based: "GOP-appointed judges"                          │
│  All quotes grounded in source text                             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 3: GENERATE REPORT                    (generate_report.py)│
│  Merge stages → Generate HTML report with statistics            │
└─────────────────────────────────────────────────────────────────┘
```

Stage 1 and stage 2 run through Anthropic's Batch API for a 50 percent cost reduction. Each extracted quote is verified against the source transcript, and 97 percent of quotes in the final report match verbatim.

## Repository Layout

```
rule_of_blah/
├── scripts/
│   ├── discover_patterns.py          # Analyze transcripts for pattern discovery
│   ├── filter_data.py                # Step 0: Filter + sample raw data
│   ├── analyze_judicial_coverage.py  # Steps 1-2: LLM analysis pipeline
│   ├── generate_report.py            # Step 3: Generate HTML report
│   ├── config.py                     # Shared configuration
│   └── prompts.py                    # LLM prompt templates
├── data/
│   └── judicial_articles.csv         # Pre-filtered articles (gitignored)
├── results/
│   ├── cnn_stage1_results.json       # Decision detection output
│   ├── cnn_stage2_results.json       # Appointment mention output
│   ├── cnn_final_results.json        # Merged results
│   ├── cnn_analysis_report.txt       # Summary statistics
│   └── cnn_report.html               # Interactive HTML report
├── pyproject.toml
└── README.md
```

## Data Sources

| Source | Dataverse Link |
|--------|----------------|
| CNN | http://dx.doi.org/10.7910/DVN/ISDPJU |
| Fox News | https://dataverse.harvard.edu/dataset.xhtml?persistentId=doi:10.7910/DVN/Q2KIES |
| MSNBC | https://dataverse.harvard.edu/dataset.xhtml?persistentId=doi:10.7910/DVN/UPJDE1 |
| NBC | http://dx.doi.org/10.7910/DVN/ND1TCV |

Results reported here are CNN only. Extending to the other three networks is a matter of running the same pipeline against the corresponding Dataverse archives.

## Usage

### Setup

```bash
uv sync
export ANTHROPIC_API_KEY="your-key-here"
```

### Full Pipeline

```bash
# Optional: Discover patterns in raw data
uv run python scripts/discover_patterns.py --raw-file data/cnn-8.csv.gz --sample 1000

# Step 0: Filter + sample raw data (download from Dataverse first)
uv run python scripts/filter_data.py --source cnn --raw-file data/cnn-8.csv.gz --sample 500 --seed 42

# Step 1: Submit decision detection batch
uv run python scripts/analyze_judicial_coverage.py --batch-submit --source cnn --stage 1

# Check status (batches complete within hours)
uv run python scripts/analyze_judicial_coverage.py --batch-status BATCH_ID

# Retrieve step 1 results
uv run python scripts/analyze_judicial_coverage.py --batch-retrieve BATCH_ID --source cnn --stage 1 \
    --articles data/cnn_judicial_articles.csv

# Step 2: Submit appointment detection batch
uv run python scripts/analyze_judicial_coverage.py --batch-submit --source cnn --stage 2 \
    --decision-results results/cnn_stage1_results.json

# Retrieve step 2 results
uv run python scripts/analyze_judicial_coverage.py --batch-retrieve BATCH_ID --source cnn --stage 2 \
    --articles data/cnn_judicial_articles.csv

# Merge results
uv run python scripts/analyze_judicial_coverage.py --merge --source cnn

# Step 3: Generate report
uv run python scripts/generate_report.py
```

### Quick Test (Synchronous)

```bash
uv run python scripts/analyze_judicial_coverage.py --pilot 5
```

## Results

- [Interactive HTML Report](https://htmlpreview.github.io/?https://github.com/soodoku/rule_of_blah/blob/main/results/cnn_report.html)
- [Full Results JSON](results/cnn_final_results.json)
- [Summary Statistics](results/cnn_analysis_report.txt)
