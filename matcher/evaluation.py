"""Accuracy of category alignment: does the top job share the resume's occupation?"""

from dataclasses import asdict, dataclass, field

import pandas as pd

from matcher.config import RANDOM_SEED, TOP_K
from matcher.datasets import sample_by_category
from matcher.matching import PairScores, ResumeJobMatcher


@dataclass
class RankedJob:
    title: str
    category: str
    score: float
    correct: bool
    matching_skills: list[str] = field(default_factory=list)
    skill_gaps: list[str] = field(default_factory=list)
    body_score: float = 0.0
    title_score: float = 0.0
    skill_score: float = 0.0


@dataclass
class ResumeResult:
    resume_id: str
    resume_category: str
    top1_correct: bool
    topk_correct: bool
    top_jobs: list[RankedJob]


@dataclass
class StageReport:
    stage: str
    resumes: int
    jobs: int
    categories: list[str]
    top1_accuracy: float
    topk_accuracy: float
    top_k: int
    by_category: list[dict]
    results: list[ResumeResult]
    comparisons: list[dict] = field(default_factory=list)
    mrr: float = 0.0

    def to_dict(self) -> dict:
        payload = asdict(self)
        return payload


def _job_text(row: pd.Series) -> str:
    return f"{row['Job Title']}\n{row['Job Description']}"


def _percent(hits: int, total: int) -> float:
    return round(100 * hits / (total or 1), 1)


def _mean_reciprocal_rank(
    scores,
    resume_categories: list[str],
    job_categories: list[str],
) -> float:
    """Mean of 1/rank for the first job whose occupation matches the resume."""
    total = 0.0
    for index, category in enumerate(resume_categories):
        order = scores[index].argsort()[::-1]
        for rank, job_index in enumerate(order, start=1):
            if job_categories[int(job_index)] == category:
                total += 1.0 / rank
                break
    return round(total / (len(resume_categories) or 1), 3)


def stage_resume_ids(
    resumes: pd.DataFrame,
    jobs: pd.DataFrame,
    stage: dict,
    seed: int = RANDOM_SEED,
) -> set[str]:
    """Resume IDs that this stage will score, so skill extraction can leave them out."""
    categories = list(stage["categories"])
    resume_sample = sample_by_category(
        resumes, "Category", categories, stage["resumes_per_category"], seed
    )
    job_sample = sample_by_category(
        jobs.dropna(subset=["category"]),
        "category",
        categories,
        stage["jobs_per_category"],
        seed,
    )
    used_categories = [
        category
        for category in categories
        if (resume_sample["Category"] == category).any()
        and (job_sample["category"] == category).any()
    ]
    chosen = resume_sample[resume_sample["Category"].isin(used_categories)]
    return set(chosen["ID"].astype(str))


def _rank_accuracy(
    scores,
    resume_categories: list[str],
    job_categories: list[str],
    top_k: int,
) -> tuple[float, float]:
    top1_hits = 0
    topk_hits = 0
    for index, category in enumerate(resume_categories):
        order = scores[index].argsort()[::-1][:top_k]
        hits = [job_categories[int(job_index)] == category for job_index in order]
        if hits and hits[0]:
            top1_hits += 1
        if any(hits):
            topk_hits += 1
    total = len(resume_categories)
    return _percent(top1_hits, total), _percent(topk_hits, total)


def evaluate_stage(
    matcher: ResumeJobMatcher,
    resumes: pd.DataFrame,
    jobs: pd.DataFrame,
    stage: dict,
    seed: int = RANDOM_SEED,
    top_k: int = TOP_K,
) -> StageReport:
    categories = list(stage["categories"])
    resume_sample = sample_by_category(
        resumes, "Category", categories, stage["resumes_per_category"], seed
    )
    job_sample = sample_by_category(
        jobs.dropna(subset=["category"]),
        "category",
        categories,
        stage["jobs_per_category"],
        seed,
    )
    used_categories = [
        category
        for category in categories
        if (resume_sample["Category"] == category).any()
        and (job_sample["category"] == category).any()
    ]
    resume_sample = resume_sample[resume_sample["Category"].isin(used_categories)].reset_index(
        drop=True
    )
    job_sample = job_sample[job_sample["category"].isin(used_categories)].reset_index(drop=True)

    resume_texts = resume_sample["Resume_str"].tolist()
    titles = job_sample["Job Title"].tolist()
    descriptions = job_sample["Job Description"].tolist()
    job_texts = [_job_text(row) for _, row in job_sample.iterrows()]
    parts: PairScores = matcher.score_parts(resume_texts, titles, descriptions)

    resume_categories = resume_sample["Category"].tolist()
    job_categories = job_sample["category"].astype(str).tolist()
    comparisons = []
    for method, matrix in (
        ("Baseline TF-IDF", parts.baseline),
        ("Text only", parts.text_only),
        ("Skill coverage only", parts.skill),
        ("Blend", parts.blend),
    ):
        top1, topk = _rank_accuracy(matrix, resume_categories, job_categories, top_k)
        mrr = _mean_reciprocal_rank(matrix, resume_categories, job_categories)
        comparisons.append(
            {
                "method": method,
                "top1_accuracy": top1,
                "topk_accuracy": topk,
                "mrr": mrr,
            }
        )

    results: list[ResumeResult] = []
    for index, resume in resume_sample.iterrows():
        order = parts.blend[index].argsort()[::-1][:top_k]
        ranked: list[RankedJob] = []
        for job_index in order:
            job_index = int(job_index)
            job = job_sample.iloc[job_index]
            correct = job["category"] == resume["Category"]
            matching, gaps = matcher.skill_gap(resume["Resume_str"], job_texts[job_index])
            ranked.append(
                RankedJob(
                    title=str(job["Job Title"]),
                    category=str(job["category"]),
                    score=round(float(parts.blend[index][job_index]) * 100, 2),
                    correct=bool(correct),
                    matching_skills=matching[:8],
                    skill_gaps=gaps[:8],
                    body_score=round(float(parts.body[index][job_index]) * 100, 2),
                    title_score=round(float(parts.title[index][job_index]) * 100, 2),
                    skill_score=round(float(parts.skill[index][job_index]) * 100, 2),
                )
            )
        results.append(
            ResumeResult(
                resume_id=str(resume["ID"]),
                resume_category=str(resume["Category"]),
                top1_correct=bool(ranked and ranked[0].correct),
                topk_correct=any(job.correct for job in ranked),
                top_jobs=ranked,
            )
        )

    by_category = []
    for category in used_categories:
        group = [item for item in results if item.resume_category == category]
        if not group:
            continue
        by_category.append(
            {
                "category": category,
                "resumes": len(group),
                "top1_accuracy": _percent(sum(item.top1_correct for item in group), len(group)),
                "topk_accuracy": _percent(sum(item.topk_correct for item in group), len(group)),
            }
        )

    total = len(results) or 1
    return StageReport(
        stage=stage["name"],
        resumes=len(results),
        jobs=len(job_sample),
        categories=used_categories,
        top1_accuracy=_percent(sum(item.top1_correct for item in results), total),
        topk_accuracy=_percent(sum(item.topk_correct for item in results), total),
        top_k=top_k,
        by_category=by_category,
        results=results,
        comparisons=comparisons,
        mrr=next(row["mrr"] for row in comparisons if row["method"] == "Blend"),
    )
