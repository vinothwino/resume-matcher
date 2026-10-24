"""Match IT and software resumes to IT job descriptions and measure role accuracy.

Examples:
  python main.py                  # small IT sample, then a larger IT sample
  python main.py --stage small    # only the small check
  python main.py --stage medium   # only the larger IT check
"""

import argparse

from matcher.config import MEDIUM_EVAL, RANDOM_SEED, SMALL_EVAL
from matcher.datasets import load_human_jobs, load_resumes, restrict_to_it_roles
from matcher.evaluation import evaluate_stage, stage_resume_ids
from matcher.matching import ResumeJobMatcher
from matcher.reporting import write_reports
from matcher.skills import extract_occupation_skills

STAGES = {"small": SMALL_EVAL, "medium": MEDIUM_EVAL}


def run(stage_names: list[str]) -> None:
    resumes, jobs = restrict_to_it_roles(load_resumes(), load_human_jobs())
    print(
        "IT / software sample: "
        f"{len(resumes):,} resumes | {len(jobs):,} jobs | "
        + ", ".join(
            f"{role} {int((resumes['Category'] == role).sum())} resumes / "
            f"{int((jobs['category'] == role).sum())} jobs"
            for role in sorted(resumes["Category"].unique())
        )
    )

    exclude_ids: set[str] = set()
    categories: list[str] = []
    for name in stage_names:
        exclude_ids |= stage_resume_ids(resumes, jobs, STAGES[name], seed=RANDOM_SEED)
        categories.extend(STAGES[name]["categories"])
    skills = extract_occupation_skills(resumes, categories, exclude_ids)
    print(f"Occupation skill lexicon: {len(skills):,} terms, excluding {len(exclude_ids):,} scored resumes")

    matcher = ResumeJobMatcher(skills)
    reports = []
    for name in stage_names:
        report = evaluate_stage(matcher, resumes, jobs, STAGES[name], seed=RANDOM_SEED)
        reports.append(report)
        print(
            f"{report.stage}: top-1 {report.top1_accuracy}% | "
            f"top-{report.top_k} {report.topk_accuracy}% | "
            f"MRR {report.mrr:.3f} | "
            f"{report.resumes} resumes x {report.jobs} jobs"
        )
        for row in report.by_category:
            print(
                f"  {row['category']}: top-1 {row['top1_accuracy']}% "
                f"top-{report.top_k} {row['topk_accuracy']}% (n={row['resumes']})"
            )

    json_path, html_path = write_reports(reports)
    print(f"Wrote {json_path}")
    print(f"Wrote {html_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Score resume-job occupation matches.")
    parser.add_argument(
        "--stage",
        choices=["small", "medium", "both"],
        default="both",
        help="small and medium both use IT roles only; medium takes more resumes and jobs per role.",
    )
    args = parser.parse_args()
    names = ["small", "medium"] if args.stage == "both" else [args.stage]
    run(names)


if __name__ == "__main__":
    main()
