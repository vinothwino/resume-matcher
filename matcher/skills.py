"""Skill lexicon built from florex/resume_corpus skills_it.txt."""

import re
import urllib.request
from collections import Counter
from pathlib import Path

from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS

from matcher.config import FLOREX_SKILLS_IT_URL, SKILLS_CACHE

MIN_PHRASE_FREQUENCY = 3
MIN_UNIGRAM_FREQUENCY = 8

BASE_SKILLS = [
    "python", "sql", "machine learning", "pandas", "java", "spring boot",
    "react", "docker", "data analysis", "scikit-learn", "rest apis",
    "tensorflow", "pytorch", "aws", "azure", "kubernetes", "excel",
    "tableau", "power bi", "javascript", "html", "css", "node.js",
    "spark", "hadoop", "nlp", "deep learning", "statistics", "r",
]

# The mined corpus is IT resumes. These phrases give the other evaluated occupations a skill signal.
OCCUPATION_SKILLS = [
    "talent acquisition", "employee relations", "onboarding", "payroll",
    "sales pipeline", "lead generation", "account management", "cold calling",
    "quota attainment", "crm",
    "adobe photoshop", "adobe illustrator", "figma", "wireframes",
    "brand identity", "ux design", "ui design",
    "financial modeling", "financial statements", "variance analysis", "budgeting",
    "credit analysis", "loan processing", "retail banking", "kyc",
    "social media marketing", "content strategy", "search engine optimization",
    "google ads", "copywriting",
    "solidworks", "autocad", "structural analysis", "hvac", "plc",
    "lesson planning", "classroom management", "curriculum development",
    "student assessment",
    "general ledger", "accounts payable", "accounts receivable",
    "bank reconciliation", "quickbooks", "gaap",
    "patient care", "vital signs", "electronic health records", "hipaa",
    "medication administration",
    "food safety", "menu planning", "haccp",
]

# Words that show up in skill lists but are not skills.
SKILL_NOISE = {
    "etc", "role", "roles", "use", "using", "including", "experience",
    "skills", "skill", "ability", "abilities", "work", "working", "strong",
    "excellent", "good", "professional", "performance", "responsible",
    "duties", "duty", "job", "jobs", "position", "positions", "company",
    "companies", "client", "clients", "project", "projects", "environment",
    "level", "levels", "general", "specific", "overall", "related", "various",
    "different", "multiple", "daily", "weekly", "monthly", "annual", "yearly",
    "full", "part", "time", "based", "within", "across", "through", "during",
    "design", "management", "development", "leadership", "analysis", "services",
    "training", "operations", "engineering", "software", "data", "sales",
    "network", "develop", "developing", "business", "customer", "team", "product",
    "marketing", "financial", "process", "requirements", "technical",
    "information", "systems", "support", "planning", "implementation",
    "integration", "standards", "testing", "monitor", "document", "functions",
}


def ensure_skills_file(cache_path: Path = SKILLS_CACHE) -> Path:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    if cache_path.exists():
        return cache_path

    request = urllib.request.Request(
        FLOREX_SKILLS_IT_URL,
        headers={"User-Agent": "resume-matcher"},
    )
    with urllib.request.urlopen(request, timeout=300) as response, cache_path.open("wb") as out:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            out.write(chunk)
    return cache_path


def _keep_skill(skill: str, frequency: int) -> bool:
    skill = skill.strip().lower()
    if not skill or len(skill) > 50 or skill in SKILL_NOISE:
        return False

    tokens = skill.split()
    if len(tokens) == 1:
        if skill in BASE_SKILLS:
            return True
        if frequency < MIN_UNIGRAM_FREQUENCY or len(skill) < 3:
            return False
        if skill in ENGLISH_STOP_WORDS:
            return False
        return re.fullmatch(r"[a-z0-9.+#/-]+", skill) is not None

    if frequency < MIN_PHRASE_FREQUENCY:
        return False
    # Drop comma-split fragments such as "and procedures" from "policies and procedures".
    if tokens[0] in ENGLISH_STOP_WORDS:
        return False
    meaningful = [
        token
        for token in tokens
        if len(token) >= 3 and token not in ENGLISH_STOP_WORDS and token not in SKILL_NOISE
    ]
    return len(meaningful) >= 1


def load_skill_lexicon(cache_path: Path = SKILLS_CACHE) -> list[str]:
    """Return skills sorted longest-first so phrase checks stay consistent."""
    corpus = ensure_skills_file(cache_path).read_text(encoding="utf-8", errors="replace")
    counts: Counter[str] = Counter()

    for block in corpus.split("::::::"):
        block = block.strip()
        if ":::" not in block:
            continue
        parts = block.split(":::", 2)
        if len(parts) < 3:
            continue
        match = re.search(
            r"Skills[:\s]+(.+?)(?:Education|Certifications|Links|Additional Information|$)",
            parts[2],
            re.I | re.S,
        )
        if not match:
            continue
        for item in re.split(r"[,;\n|]", match.group(1)):
            skill = re.sub(
                r"\(\s*(?:less than 1 year|\d+\s*years?)\s*\)",
                "",
                item,
                flags=re.I,
            ).strip(" .")
            if 2 <= len(skill) <= 50 and re.search(r"[a-zA-Z]", skill):
                counts[skill.lower()] += 1

    kept = {skill for skill, count in counts.items() if _keep_skill(skill, count)}
    return sorted(set(BASE_SKILLS) | set(OCCUPATION_SKILLS) | kept, key=len, reverse=True)


def extract_occupation_skills(
    resumes,
    categories: list[str],
    exclude_ids: set[str],
    min_in_category: int = 5,
    max_per_category: int = 25,
) -> list[str]:
    """Distinctive terms from other resumes in each occupation, excluding the scored resumes."""
    from sklearn.feature_extraction.text import CountVectorizer

    from matcher.matching import clean_text

    frame = resumes.copy()
    frame["ID"] = frame["ID"].astype(str)
    held = frame[~frame["ID"].isin({str(item) for item in exclude_ids})].copy()
    categories = list(dict.fromkeys(categories))
    held = held[held["Category"].isin(categories)].reset_index(drop=True)
    if held.empty:
        return []

    vectorizer = CountVectorizer(
        stop_words="english",
        ngram_range=(1, 2),
        min_df=5,
        max_df=0.4,
        binary=True,
        max_features=8000,
        token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z+#.]{2,}\b",
    )
    matrix = vectorizer.fit_transform(held["Resume_str"].fillna("").map(clean_text))
    terms = vectorizer.get_feature_names_out()
    labels = held["Category"].tolist()
    chosen: list[str] = []
    for category in categories:
        mask = np_mask(labels, category)
        n_in = int(mask.sum())
        n_out = int((~mask).sum())
        if n_in < min_in_category or n_out == 0:
            continue
        import numpy as np

        in_counts = np.asarray(matrix[mask].sum(axis=0)).ravel()
        out_counts = np.asarray(matrix[~mask].sum(axis=0)).ravel()
        rate_in = in_counts / n_in
        rate_out = out_counts / n_out
        scored: list[tuple[float, str]] = []
        for index, term in enumerate(terms):
            tokens = str(term).split()
            if in_counts[index] < min_in_category or rate_in[index] < 0.12:
                continue
            if rate_in[index] < 2.5 * rate_out[index]:
                continue
            if all(token in SKILL_NOISE or token in ENGLISH_STOP_WORDS for token in tokens):
                continue
            scored.append((float(rate_in[index] - rate_out[index]), str(term)))
        scored.sort(reverse=True)
        picked = [term for _, term in scored[:max_per_category]]
        phrases = [term for term in picked if " " in term]
        for term in picked:
            if " " not in term and any(term in phrase.split() for phrase in phrases):
                continue
            chosen.append(term)
    return sorted(set(chosen), key=len, reverse=True)


def np_mask(labels: list[str], category: str):
    import numpy as np

    return np.array([label == category for label in labels])
