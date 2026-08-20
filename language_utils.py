"""Small deterministic language-normalization helpers; no model or network calls."""

from difflib import get_close_matches, SequenceMatcher
import re


ALIASES = {
    "whats": "what", "wht": "what", "wat": "what", "wot": "what",
    "hows": "how", "hwo": "how", "y": "why", "pls": "please",
    "viz": "visual", "visualization": "visual", "visualisation": "visual",
    "graph": "visual", "chart": "visual", "plot": "visual", "figure": "visual",
    "positively": "positive", "positve": "positive", "postive": "positive",
    "negatively": "negative", "negatve": "negative", "negetive": "negative",
    "improvd": "improved", "improvde": "improve", "improving": "improve",
    "improvement": "improve", "improvements": "improve", "betterment": "improve",
    "worsened": "worse", "worsening": "worse", "declined": "decline",
    "declining": "decline", "happened": "happen", "happening": "happen",
    "happend": "happen", "hapen": "happen", "tells": "tell", "telling": "tell",
    "means": "mean", "meaning": "mean", "explains": "explain",
    "interested": "interest", "interesting": "interest", "importance": "important",
    "callouts": "callout", "warnings": "warning", "concerns": "concern",
    "risks": "risk", "outputs": "output", "results": "result",
    "calculated": "calculate", "calculating": "calculate", "calculation": "calculate",
    "metrics": "metric", "limitations": "limit", "caveats": "caveat",
    "recommendations": "recommend", "recommended": "recommend",
    "actions": "action", "priorities": "priority", "strengths": "strength",
    "weaknesses": "weakness", "wins": "win", "winning": "win",
    "issues": "issue", "problems": "problem", "downsides": "downside",
    "redflags": "redflag", "wrong": "problem",
    "best": "good", "worst": "bad", "upside": "positive", "worrying": "concern",
    "worried": "concern", "cares": "care", "outliers": "outlier", "stands": "stand",
    "profit": "margin", "profits": "margin", "financial": "margin", "money": "margin",
    "nurses": "workforce", "nursing": "workforce", "staffing": "workforce",
}

VOCABULARY = {
    "what", "why", "how", "where", "which", "tell", "mean", "explain", "show",
    "summarize", "understand", "interpret", "read", "happen", "visual", "output",
    "result", "data", "good", "positive", "better", "improve", "win", "strength",
    "bad", "negative", "worse", "decline", "concern", "risk", "problem", "weakness", "issue", "downside", "redflag",
    "focus", "important", "interest", "attention", "priority", "matter", "celebrate",
    "action", "fix", "change", "next", "step", "recommend", "respond", "do", "can",
    "could", "should", "callout", "warning", "caution", "note", "annotation", "highlight",
    "calculate", "metric", "axis", "legend", "measure", "method", "formula", "derive",
    "limit", "trust", "reliable", "confidence", "bias", "missing", "executive", "summary",
    "leadership", "ceo", "performance", "trend", "recent", "month", "day", "dashboard",
    "about", "overview", "help", "work", "working", "not", "well", "care", "flag", "stand", "out", "outlier", "most", "please", "current", "prior",
    "margin", "workforce", "nurse", "staff", "quality", "flow", "finance", "access", "experience", "privacy", "equity", "roi",
}

STOPWORDS = {"the", "a", "an", "is", "are", "was", "were", "this", "that", "these", "those", "i", "we", "me", "my", "our", "it", "in", "on", "of", "to", "for", "and", "or", "about", "please"}
DOMAIN_TOKENS = {"margin", "workforce", "nurse", "staff", "quality", "flow", "finance", "access", "experience", "privacy", "equity", "roi", "risk", "warning", "callout", "calculate", "limit"}


def normalized_text(text):
    return re.sub(r"[^a-z0-9]+", " ", str(text).lower()).strip()


def flexible_tokens(text):
    """Normalize common variants and cautiously correct close domain-word typos."""
    output = []
    for raw in normalized_text(text).split():
        token = ALIASES.get(raw, raw)
        if token not in VOCABULARY and token not in ALIASES.values() and token.isalpha() and len(token) >= 4:
            match = get_close_matches(token, VOCABULARY, n=1, cutoff=0.79)
            if match:
                token = match[0]
        output.append(ALIASES.get(token, token))
    return set(output)


def extracted_keywords(text):
    return sorted(token for token in flexible_tokens(text) if token not in STOPWORDS and len(token) > 1)


def closest_suggestions(question, candidates, limit=3):
    """Rank only allowlisted questions; never generate a new executable query."""
    source_tokens = set(extracted_keywords(question))
    source_text = normalized_text(question)
    ranked = []
    for index, candidate in enumerate(candidates):
        candidate_tokens = set(extracted_keywords(candidate))
        union = source_tokens | candidate_tokens
        overlap = len(source_tokens & candidate_tokens) / len(union) if union else 0.0
        phrase = SequenceMatcher(None, source_text, normalized_text(candidate)).ratio()
        # Shared intent/domain keywords matter more than character similarity.
        domain_overlap = len((source_tokens & candidate_tokens) & DOMAIN_TOKENS)
        score = 0.72 * overlap + 0.28 * phrase + 0.30 * domain_overlap
        ranked.append((score, -index, candidate))
    ranked.sort(reverse=True)
    return [candidate for _, _, candidate in ranked[:max(1, limit)]]
