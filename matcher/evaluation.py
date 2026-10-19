"""Accuracy of category alignment: does the top job share the resume's occupation?"""

from dataclasses import asdict, dataclass, field

import pandas as pd

from matcher.config import RANDOM_SEED, TOP_K
from matcher.datasets import sample_by_category
from matcher.matching import ResumeJobMatcher


@dataclass
class RankedJob:
    title: str
    category: str
    score: float
    correct: bool
    matching_skills: list[str] = field(default_factory=list)
    skill_gaps: list[str] = field(default_factory=list)


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

    def to_dict(self) -> dict:
        payload = asdict(self)
        return payload


def _job_text(row: pd.Series) -> str:
    return f"{row['Job Title']}\n{row['Job Description']}"


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
    job_texts = [_job_text(row) for _, row in job_sample.iterrows()]
    scores = matcher.similarity(resume_texts, job_texts)

    results: list[ResumeResult] = []
    for index, resume in resume_sample.iterrows():
        order = scores[index].argsort()[::-1][:top_k]
        ranked: list[RankedJob] = []
        for job_index in order:
            job = job_sample.iloc[int(job_index)]
            correct = job["category"] == resume["Category"]
            matching, gaps = matcher.skill_gap(resume["Resume_str"], job_texts[int(job_index)])
            ranked.append(
                RankedJob(
                    title=str(job["Job Title"]),
                    category=str(job["category"]),
                    score=round(float(scores[index][job_index]) * 100, 2),
                    correct=bool(correct),
                    matching_skills=matching[:8],
                    skill_gaps=gaps[:8],
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
                "top1_accuracy": round(
                    100 * sum(item.top1_correct for item in group) / len(group), 1
                ),
                "topk_accuracy": round(
                    100 * sum(item.topk_correct for item in group) / len(group), 1
                ),
            }
        )

    total = len(results) or 1
    return StageReport(
        stage=stage["name"],
        resumes=len(results),
        jobs=len(job_sample),
        categories=used_categories,
        top1_accuracy=round(100 * sum(item.top1_correct for item in results) / total, 1),
        topk_accuracy=round(100 * sum(item.topk_correct for item in results) / total, 1),
        top_k=top_k,
        by_category=by_category,
        results=results,
    )
