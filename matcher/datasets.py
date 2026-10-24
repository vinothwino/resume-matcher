"""Load Kaggle resumes and job postings, and label jobs by title."""

import re

import pandas as pd
import kagglehub
from kagglehub import KaggleDatasetAdapter

from matcher.config import (
    CATEGORY_TITLE_KEYWORDS,
    IT_ROLE_KEYWORDS,
    JOB_DATASET,
    JOB_FILE,
    RESUME_DATASET,
    RESUME_FILE,
)


_KEYWORD_RULES: list[tuple[str, str]] = sorted(
    (
        (keyword, category)
        for category, keywords in CATEGORY_TITLE_KEYWORDS.items()
        for keyword in keywords
    ),
    key=lambda item: len(item[0]),
    reverse=True,
)


def category_from_title(title: str) -> str | None:
    lowered = f" {str(title).lower()} "
    for keyword, category in _KEYWORD_RULES:
        if f" {keyword} " in lowered or lowered.strip() == keyword:
            return category
    return None


_IT_ROLE_RULES: list[tuple[str, str]] = sorted(
    (
        (keyword, role)
        for role, keywords in IT_ROLE_KEYWORDS.items()
        for keyword in keywords
    ),
    key=lambda item: len(item[0]),
    reverse=True,
)


def it_role(text: str) -> str | None:
    """Longest IT role phrase in text. Used only on IT resumes and IT job titles."""
    normalized = re.sub(r"[^a-z0-9+#.\s]", " ", str(text).lower())
    normalized = re.sub(r"\s+", " ", normalized).strip()
    padded = f" {normalized} "
    for keyword, role in _IT_ROLE_RULES:
        if f" {keyword} " in padded:
            return role
    return None


def restrict_to_it_roles(
    resumes: pd.DataFrame, jobs: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Keep IT resumes and IT jobs, labeled as software, systems, or IT support."""
    it_resumes = resumes[resumes["Category"] == "INFORMATION-TECHNOLOGY"].copy()
    it_resumes["Category"] = it_resumes["Resume_str"].map(it_role)
    it_resumes = it_resumes[it_resumes["Category"].notna()].reset_index(drop=True)

    it_jobs = jobs[jobs["category"] == "INFORMATION-TECHNOLOGY"].copy()
    it_jobs["category"] = it_jobs["Job Title"].map(it_role)
    it_jobs = it_jobs[it_jobs["category"].notna()].reset_index(drop=True)
    return it_resumes, it_jobs


def load_resumes() -> pd.DataFrame:
    frame = kagglehub.dataset_load(
        KaggleDatasetAdapter.PANDAS,
        RESUME_DATASET,
        RESUME_FILE,
    )
    frame = frame.copy()
    frame["Category"] = frame["Category"].astype(str).str.upper()
    frame["Resume_str"] = frame["Resume_str"].fillna("").astype(str)
    return frame


def load_human_jobs() -> pd.DataFrame:
    frame = kagglehub.dataset_load(
        KaggleDatasetAdapter.PANDAS,
        JOB_DATASET,
        JOB_FILE,
    )
    frame = frame[frame["Is Fake"] == "Human-Written"].copy()
    frame["Job Title"] = frame["Job Title"].fillna("").astype(str)
    frame["Job Description"] = frame["Job Description"].fillna("").astype(str)
    frame["category"] = frame["Job Title"].map(category_from_title)
    return frame.reset_index(drop=True)


def sample_by_category(
    frame: pd.DataFrame,
    category_column: str,
    categories: list[str],
    per_category: int,
    seed: int,
) -> pd.DataFrame:
    """Take up to `per_category` rows for each requested category."""
    pieces = []
    for category in categories:
        pool = frame[frame[category_column] == category]
        if pool.empty:
            continue
        take = min(per_category, len(pool))
        pieces.append(pool.sample(n=take, random_state=seed))
    if not pieces:
        return frame.iloc[0:0].copy()
    return pd.concat(pieces, ignore_index=True)
