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
    return sorted(set(BASE_SKILLS) | kept, key=len, reverse=True)
