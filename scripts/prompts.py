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

Find ALL mentions (explicit or implicit) that indicate who appointed the judges/justices:

EXPLICIT examples:
- "appointed by President X"
- "X's nominee"
- "nominated by President X"
- "X appointee"

IMPLICIT examples:
- "conservative majority" (implies Republican appointees)
- "liberal justices" (implies Democratic appointees)
- "Trump-era appointees"
- "the three justices added by Trump"
- "Obama's picks"

PARTY examples:
- "GOP-nominated judges"
- "Republican-appointed"
- "Democrat-appointed"

Return JSON:
{{
  "has_appointment_mentions": true/false,
  "mentions": [
    {{
      "quote": "EXACT text from article (copy verbatim)",
      "type": "explicit" | "implicit" | "party",
      "president": "Trump" | "Biden" | "Obama" | "Bush" | "Clinton" | "Reagan" | "Carter" | "unknown",
      "judge_name": "name if mentioned, else null",
      "context": "brief description of what this mention conveys"
    }}
  ],
  "total_explicit_mentions": 0,
  "total_implicit_mentions": 0,
  "total_party_mentions": 0
}}

CRITICAL REQUIREMENTS:
1. The "quote" field must contain text that appears EXACTLY in the article - do not paraphrase
2. Include partial quotes if needed, but they must be verbatim
3. If no appointment mentions exist, set has_appointment_mentions to false and mentions to []
4. Be thorough - capture even subtle references to judicial appointments"""
