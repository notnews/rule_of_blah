"""LLM prompt templates for judicial coverage analysis."""

DECISION_DETECTION_PROMPT = """Analyze this news transcript to determine if it covers an actual Supreme Court or federal circuit court DECISION.

A court DECISION means the court ruled, decided, struck down, upheld, or issued a judgment on a case.

ARTICLE:
{text}

Return JSON:
{{
  "covers_court_decision": true/false,
  "decision_type": "supreme_court" | "circuit_court" | "both" | null,
  "evidence_quotes": ["quote1", "quote2"],
  "case_name": "if mentioned, e.g. Roe v. Wade" or null,
  "brief_summary": "1 sentence summary of the decision if applicable"
}}

IMPORTANT:
- Only return true for covers_court_decision if the article discusses an actual ruling/decision
- Mentioning judges or courts without discussing a decision = false
- Evidence quotes must appear EXACTLY in the article"""

APPOINTMENT_DETECTION_PROMPT = """Analyze this news transcript for ALL mentions of who appointed judges or justices involved in the covered court decision.

ARTICLE:
{text}

Find ALL mentions that indicate who appointed the judges/justices. Categorize by what is explicitly named:

PRESIDENT (names a specific president):
- "appointed by President Trump"
- "Trump appointee"
- "Trump-era judges"
- "nominated by Obama"
- "the three justices added by Trump"
- "Biden's pick"

PARTY (names party, but not a specific president):
- "Republican-appointed judges"
- "GOP nominees"
- "Democrat-appointed"
- "judges appointed by Democrats"

IDEOLOGICAL (uses ideology, names neither president nor party - reader must infer):
- "conservative majority"
- "liberal justices"
- "the court's right wing"
- "originalist judges"

Return JSON:
{{
  "has_appointment_mentions": true/false,
  "mentions": [
    {{
      "quote": "EXACT text from article (copy verbatim)",
      "type": "president" | "party" | "ideological",
      "president": "Trump" | "Biden" | "Obama" | "Bush" | "Clinton" | "Reagan" | "Carter" | "unknown",
      "judge_name": "name if mentioned, else null",
      "context": "brief description of what this mention conveys"
    }}
  ],
  "total_president_mentions": 0,
  "total_party_mentions": 0,
  "total_ideological_mentions": 0
}}

CRITICAL REQUIREMENTS:
1. The "quote" field must contain text that appears EXACTLY in the article - do not paraphrase
2. Include partial quotes if needed, but they must be verbatim
3. If no appointment mentions exist, set has_appointment_mentions to false and mentions to []
4. Be thorough - capture even subtle references to judicial appointments
5. ONLY extract SPOKEN dialogue - NOT chyrons, graphics, or on-screen text
6. Skip phrases that are ALL CAPS (these are typically chyrons/graphics, e.g., "SUPREME COURT NOMINEE")
7. Quotes must be substantive - at least 20 characters of actual speech"""
