"""TF-IDF similarity and skill overlap between resumes and jobs."""

import re
from dataclasses import dataclass

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from matcher.config import BODY_WEIGHT, SKILL_WEIGHT, TITLE_WEIGHT


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


@dataclass
class PairScores:
    """Resume x job matrices in [0, 1]. `blend` is the ranking score."""

    baseline: np.ndarray
    body: np.ndarray
    title: np.ndarray
    skill: np.ndarray
    text_only: np.ndarray
    semantic: np.ndarray
    blend: np.ndarray


class ResumeJobMatcher:
    def __init__(self, skills: list[str], max_features: int = 8000):
        self.skills = SkillIndex(skills)
        self.max_features = max_features
        self._semantic_model = None

    def _cosine(self, left: list[str], right: list[str]) -> np.ndarray:
        if not left or not right:
            return np.zeros((len(left), len(right)))
        vectorizer = TfidfVectorizer(stop_words="english", max_features=self.max_features)
        matrix = vectorizer.fit_transform(
            [clean_text(text) for text in left] + [clean_text(text) for text in right]
        )
        scores = cosine_similarity(matrix[: len(left)], matrix[len(left) :])
        return np.clip(scores, 0.0, 1.0)

    def similarity(self, resumes: list[str], jobs: list[str]) -> np.ndarray:
        """Baseline: TF-IDF cosine of each resume against title and description concatenated."""
        return self._cosine(resumes, jobs)

    def _sentence_model(self):
        if self._semantic_model is None:
            from sentence_transformers import SentenceTransformer

            self._semantic_model = SentenceTransformer("all-MiniLM-L6-v2")
        return self._semantic_model

    def _embed_documents(self, texts: list[str]) -> np.ndarray:
        """Mean of chunk embeddings so a long resume is not cut off after the opening."""
        model = self._sentence_model()
        vectors = []
        for text in texts:
            words = str(text).split()
            parts = [" ".join(words[start : start + 180]) for start in range(0, max(len(words), 1), 180)]
            if not parts:
                parts = [""]
            encoded = np.asarray(
                model.encode(parts, normalize_embeddings=True, show_progress_bar=False)
            )
            mean = encoded.mean(axis=0)
            norm = np.linalg.norm(mean)
            vectors.append(mean / norm if norm else mean)
        return np.vstack(vectors)

    def semantic_similarity(self, resumes: list[str], jobs: list[str]) -> np.ndarray:
        """Cosine of sentence embeddings. This is the semantic match, separate from TF-IDF."""
        if not resumes or not jobs:
            return np.zeros((len(resumes), len(jobs)))
        left = self._embed_documents(resumes)
        right = self._embed_documents(jobs)
        scores = np.matmul(left, right.T)
        return np.clip(scores, 0.0, 1.0)

    def skill_coverage(self, resumes: list[str], jobs: list[str]) -> np.ndarray:
        """Share of each job's lexicon skills that also appear on the resume."""
        if not resumes or not jobs:
            return np.zeros((len(resumes), len(jobs)))
        resume_sets = [self.skills.extract(text) for text in resumes]
        job_sets = [self.skills.extract(text) for text in jobs]
        scores = np.zeros((len(resumes), len(jobs)))
        for i, resume_skills in enumerate(resume_sets):
            for j, job_skills in enumerate(job_sets):
                if job_skills:
                    scores[i, j] = len(resume_skills & job_skills) / len(job_skills)
        return scores

    def score_parts(
        self,
        resumes: list[str],
        titles: list[str],
        descriptions: list[str],
    ) -> PairScores:
        combined = [f"{title}\n{description}" for title, description in zip(titles, descriptions)]
        baseline = self.similarity(resumes, combined)
        body = self._cosine(resumes, descriptions)
        title = self._cosine(resumes, titles)
        skill = self.skill_coverage(resumes, combined)
        semantic = self.semantic_similarity(resumes, combined)
        text_weight = BODY_WEIGHT + TITLE_WEIGHT
        text_only = (BODY_WEIGHT * body + TITLE_WEIGHT * title) / text_weight
        blend = BODY_WEIGHT * body + TITLE_WEIGHT * title + SKILL_WEIGHT * skill
        return PairScores(
            baseline=baseline,
            body=body,
            title=title,
            skill=skill,
            text_only=text_only,
            semantic=semantic,
            blend=blend,
        )

    def skill_gap(self, resume_text: str, job_text: str) -> tuple[list[str], list[str]]:
        resume_skills = self.skills.extract(resume_text)
        job_skills = self.skills.extract(job_text)
        matching = sorted(resume_skills & job_skills)
        gaps = sorted(job_skills - resume_skills)
        return matching, gaps
