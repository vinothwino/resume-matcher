"""TF-IDF similarity and skill overlap between resumes and jobs."""

import re

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def clean_text(text: str) -> str:
    text = str(text).lower()
    text = re.sub(r"[^a-zA-Z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _match_blob(text: str) -> str:
    text = str(text).lower()
    text = re.sub(r"[^a-zA-Z0-9\s.]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return f" {text} "


class SkillIndex:
    def __init__(self, skills: list[str]):
        self.unigrams = [skill for skill in skills if " " not in skill]
        self.phrases = [skill for skill in skills if " " in skill]

    def extract(self, text: str) -> set[str]:
        blob = _match_blob(text)
        words = set(blob.split())
        found = {skill for skill in self.unigrams if skill in words}
        found.update(skill for skill in self.phrases if f" {skill} " in blob)
        return found


class ResumeJobMatcher:
    def __init__(self, skills: list[str], max_features: int = 8000):
        self.skills = SkillIndex(skills)
        self.max_features = max_features

    def similarity(self, resumes: list[str], jobs: list[str]) -> np.ndarray:
        """Return a resume x job cosine matrix in [0, 1]."""
        if not resumes or not jobs:
            return np.zeros((len(resumes), len(jobs)))
        vectorizer = TfidfVectorizer(stop_words="english", max_features=self.max_features)
        matrix = vectorizer.fit_transform(
            [clean_text(text) for text in resumes] + [clean_text(text) for text in jobs]
        )
        resume_vectors = matrix[: len(resumes)]
        job_vectors = matrix[len(resumes) :]
        return cosine_similarity(resume_vectors, job_vectors)

    def skill_gap(self, resume_text: str, job_text: str) -> tuple[list[str], list[str]]:
        resume_skills = self.skills.extract(resume_text)
        job_skills = self.skills.extract(job_text)
        matching = sorted(resume_skills & job_skills)
        gaps = sorted(job_skills - resume_skills)
        return matching, gaps
