## The Rule of Blah

In its classical formulation, the rule of law demands that legal outcomes be determined by neutral application of declared rules, not by the arbitrary whims or political affiliations of decision‑makers. Impartiality and consistency lie at its core: as Dicey put it, "no man is punishable or can lawfully be made to suffer in body or goods except for a distinct breach of law established in the ordinary legal manner before the ordinary courts of the land" (A.V. Dicey, Introduction to the Study of the Law of the Constitution, 1885). If judges' decisions systematically vary with their partisan backgrounds, then predictability—and public confidence in equal treatment—erodes.

Empirical evidence leaves little doubt that partisanship shapes judicial outcomes even in "rule‑bound" contexts. At the Supreme Court level, Segal & Spaeth's influential attitudinal model shows that justices' votes correlate strongly with their perceived policy preferences, explaining roughly two‑thirds of ideological variance in civil‑liberties cases purely by their Segal–Cover scores (r²≈0.64). That finding implies that legal reasoning often bows to personal ideology, undercutting the ideal of neutral rule‑application.

In the lower courts, the pattern persists. A Harvard study of federal sentencing before and after United States v. Booker finds that judges appointed by Republican presidents impose sentences three months longer on average than their Democratic counterparts—and that Republican‑appointed judges give significantly harsher terms to Black defendants, even controlling for offense and criminal‑history scores . More recently, Schanzenbach & Tiller link over half a million federal sentencing records to individual judge identities, demonstrating that Republican‑appointed judges consistently impose longer sentences than Democratic‑appointed peers, with judge‑fixed effects ruling out court‑level confounders.

These systematic divergences conflict with the rule‑of‑law ideal: if two citizens commit identical offenses but face different sentences based solely on the appointing president's party, then equality before the law is compromised. And it isn't limited to criminal sentencing. Alma Cohen's analysis of 670,000 Circuit Court cases finds that panels with more Republican‑appointed judges are measurably less likely to side with the "weaker" party (e.g., civil plaintiffs vs. government, immigrants vs. agency) even in non‑controversial domains.

Given this empirical backdrop, it's natural to ask: how often does the news media flag the appointing president's party when reporting on judicial decisions? If media outlets seldom mention partisanship, the public may wrongly assume that judges decide solely on law. Conversely, frequent partisan attributions could reflect—and reinforce—a growing skepticism about judicial impartiality, itself a symptom of rule‑of‑law erosion.

A media analysis can therefore serve two purposes. First, it measures public discourse around judicial impartiality: how aware are readers that party‑affiliation shapes outcomes? Second, it provides a barometer of institutional legitimacy—if mainstream outlets routinely couch decisions in partisan terms, that signals an expectation that lawmaking is inherently political.

To motivate your corpus study, note that prior research on media framing (e.g. Cohen & Davis, 2016) shows that attributing judicial behavior to party can increase public cynicism and reduce perceived legitimacy of court rulings. By quantifying the frequency and context of partisan mentions—stratified by outlet, case type, and ideological salience—you can trace how media coverage interacts with empirical realities of judicial behavior.

In sum, the media's invocation of a judge's partisan pedigree is not neutral "color commentary," but a lens on the health of the rule of law. When reporting neglects to note the strong empirical link between affiliation and outcomes, it perpetuates the myth of purely legal adjudication; when it over‑emphasizes partisanship, it fuels public distrust. Your analysis will thus shed light on the uneasy balance between legal ideal and political reality in both courtrooms and newsrooms.

## Research Question

How often does news media mention who appointed judges when covering court decisions?

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

## Methodology

### Two-Stage LLM Pipeline

**Stage 1 - Decision Detection:** Claude Sonnet analyzes each article to determine if it covers an actual Supreme Court or federal circuit court decision (ruling, judgment, opinion).

**Stage 2 - Appointment Mention Extraction:** For articles covering decisions, the LLM identifies all mentions of who appointed judges, including:
- **Explicit:** "appointed by President Trump", "Biden nominee"
- **Implicit:** "conservative majority", "Trump-era court"
- **Party-based:** "GOP-appointed judges", "Republican nominees"

All extracted quotes are grounded—they must appear verbatim in the source text. Quote verification confirms 97% accuracy.

### Cost Optimization

Uses Anthropic's Message Batches API for 50% cost reduction compared to synchronous API calls. Batches typically complete within hours.

## Repository Layout

```
rule_of_blah/
├── analyze_judicial_coverage.py  # Main analysis pipeline (batch API)
├── prompts.py                    # LLM prompt templates
├── generate_report.py            # HTML report generator
├── judicial_filter.ipynb         # Initial filtering notebook
├── judicial_articles.csv         # Pre-filtered CNN articles
├── pyproject.toml                # Project configuration and dependencies
└── results/
    ├── cnn_stage1_results.json   # Decision detection results
    ├── cnn_stage2_results.json   # Appointment mention results
    ├── cnn_final_results.json    # Merged results
    ├── cnn_analysis_report.txt   # Summary statistics
    └── cnn_report.html           # Interactive HTML report
```

## Data Sources

| Source | Dataverse Link |
|--------|----------------|
| CNN | http://dx.doi.org/10.7910/DVN/ISDPJU |
| Fox News | https://dataverse.harvard.edu/dataset.xhtml?persistentId=doi:10.7910/DVN/Q2KIES |
| MSNBC | https://dataverse.harvard.edu/dataset.xhtml?persistentId=doi:10.7910/DVN/UPJDE1 |
| NBC | http://dx.doi.org/10.7910/DVN/ND1TCV |

## Usage

### Installation

```bash
uv sync
export ANTHROPIC_API_KEY="your-key-here"
```

### Run Pilot (Synchronous)

```bash
python analyze_judicial_coverage.py --pilot 5
```

### Batch Processing Workflow

```bash
# Stage 1: Decision detection
python analyze_judicial_coverage.py --batch-submit --source cnn --stage 1

# Check status
python analyze_judicial_coverage.py --batch-status BATCH_ID

# Retrieve results
python analyze_judicial_coverage.py --batch-retrieve BATCH_ID --source cnn --stage 1 --articles judicial_articles.csv

# Stage 2: Appointment mentions (only for articles with decisions)
python analyze_judicial_coverage.py --batch-submit --source cnn --stage 2 --decision-results results/cnn_stage1_results.json

# Retrieve and merge
python analyze_judicial_coverage.py --batch-retrieve BATCH_ID --source cnn --stage 2 --articles judicial_articles.csv
python analyze_judicial_coverage.py --merge --source cnn
```

### Generate Report

```bash
python generate_report.py
```

## Results

- [Interactive HTML Report](results/cnn_report.html)
- [Full Results JSON](results/cnn_final_results.json)
- [Summary Statistics](results/cnn_analysis_report.txt)
