"""
Deterministic (non-AI) helpers that support the AI-driven ATS analysis:
 - local keyword extraction / fuzzy matching as a fast fallback and sanity check
 - structural formatting checks on the original DOCX (tables, columns, images)
   which a language model cannot reliably see, so we compute them in code.
"""
import re
from collections import Counter

from rapidfuzz import fuzz

STOPWORDS = {
    'the', 'a', 'an', 'and', 'or', 'to', 'of', 'in', 'on', 'for', 'with',
    'is', 'are', 'as', 'at', 'by', 'be', 'this', 'that', 'will', 'we', 'you',
    'our', 'your', 'their', 'it', 'from', 'have', 'has', 'not', 'but', 'able',
}


def extract_candidate_keywords(text: str, top_n: int = 40) -> list[str]:
    """Very lightweight noun/technology-ish keyword extraction, used as a fallback
    when the AI is unavailable or as a sanity cross-check on its output."""
    words = re.findall(r"[A-Za-z][A-Za-z0-9+.#/-]{1,}", text)
    words = [w for w in words if w.lower() not in STOPWORDS and len(w) > 1]
    counts = Counter(w.strip('.,') for w in words)
    ranked = [w for w, _ in counts.most_common(top_n * 3)]
    # prefer capitalized / technology-looking tokens first
    tech_like = [w for w in ranked if re.match(r'^[A-Z][a-zA-Z0-9+.#]*$', w) or any(c in w for c in '+#.')]
    rest = [w for w in ranked if w not in tech_like]
    return (tech_like + rest)[:top_n]


def fuzzy_keyword_match(resume_text: str, keywords: list[str], threshold: int = 80) -> tuple[list, list]:
    """Return (matched, missing) keyword lists using fuzzy substring matching,
    so 'PostgreSQL' still matches 'Postgres' etc."""
    resume_lower = resume_text.lower()
    matched, missing = [], []
    for kw in keywords:
        kw_lower = kw.lower().strip()
        if not kw_lower:
            continue
        if kw_lower in resume_lower:
            matched.append(kw)
            continue
        score = fuzz.partial_ratio(kw_lower, resume_lower)
        if score >= threshold:
            matched.append(kw)
        else:
            missing.append(kw)
    return matched, missing


def check_docx_formatting(docx_path: str) -> dict:
    """Inspect a DOCX file for ATS-unfriendly formatting: tables, multi-column
    sections, and embedded images, which language models cannot see directly."""
    import docx
    result = {
        'tables_detected': False,
        'images_detected': False,
        'columns_detected': False,
        'section_count': 0,
    }
    try:
        document = docx.Document(docx_path)
        result['tables_detected'] = len(document.tables) > 0
        result['section_count'] = len(document.sections)
        for sec in document.sections:
            if getattr(sec, 'text_columns', None) and sec.text_columns.number > 1:
                result['columns_detected'] = True
        image_count = 0
        for rel in document.part.rels.values():
            if 'image' in rel.reltype:
                image_count += 1
        result['images_detected'] = image_count > 0
    except Exception:  # noqa: BLE001
        pass
    return result


def keyword_density(text: str, keyword: str) -> float:
    words = re.findall(r"\w+", text.lower())
    if not words:
        return 0.0
    occurrences = sum(1 for w in words if w == keyword.lower())
    return round((occurrences / len(words)) * 100, 3)


_LEADING_STOPWORDS = {
    'built', 'led', 'designed', 'developed', 'managed', 'created', 'implemented',
    'improved', 'delivered', 'worked', 'used', 'utilized', 'collaborated', 'reduced',
    'increased', 'achieved', 'responsible', 'this', 'the', 'a', 'an', 'i', 'my',
    'drove', 'launched', 'owned', 'oversaw', 'spearheaded', 'contributed', 'helped',
}


def extract_facts(text: str) -> dict:
    """Pull out the 'hard facts' from a resume: bare numbers/years (compared
    digit-only, so '35%' and '35 percent' are treated as equivalent) and
    multi-word proper nouns (likely employer/school/product names, with
    leading sentence-starter verbs stripped out to avoid false positives)."""
    numbers = set(re.findall(r"\d[\d,]*(?:\.\d+)?", text))
    numbers = {n.replace(',', '') for n in numbers if len(n.replace(',', '')) >= 2}

    proper_nouns = set()
    for match in re.finditer(r"\b(?:[A-Z][a-zA-Z0-9&.]*\s){1,3}[A-Z][a-zA-Z0-9&.]*\b", text):
        words = match.group(0).split()
        while words and words[0].lower() in _LEADING_STOPWORDS:
            words = words[1:]
        if len(words) >= 2:
            proper_nouns.add(' '.join(words))

    return {'numbers': numbers, 'proper_nouns': proper_nouns}


def check_factual_fidelity(original_text: str, rewritten_text: str) -> list:
    """Return the list of hard facts present in the original resume that are
    missing from the rewritten version - a lightweight, deterministic
    safety net layered on top of the AI rewrite instructions."""
    original_facts = extract_facts(original_text)
    rewritten_lower = rewritten_text.lower()
    rewritten_digits = set(re.findall(r"\d[\d,]*(?:\.\d+)?", rewritten_text))
    rewritten_digits = {n.replace(',', '') for n in rewritten_digits}

    dropped = []
    for number in original_facts['numbers']:
        if number not in rewritten_digits:
            dropped.append(number)

    for phrase in original_facts['proper_nouns']:
        if phrase.lower() in rewritten_lower:
            continue
        score = fuzz.partial_ratio(phrase.lower(), rewritten_lower)
        if score < 90:
            dropped.append(phrase)

    return sorted(set(dropped))
