"""Match resumes to job descriptions and measure occupation accuracy.

Examples:
  python main.py                  # small labeled set, then a larger mixed set
  python main.py --stage small    # only the small check
  python main.py --stage medium   # only the diverse medium check
"""

import argparse

from matcher.config import MEDIUM_EVAL, RANDOM_SEED, SMALL_EVAL
from matcher.datasets import load_human_jobs, load_resumes
from matcher.evaluation import evaluate_stage
from matcher.matching import ResumeJobMatcher
from matcher.reporting import write_reports
from matcher.skills import load_skill_lexicon

STAGES = {"small": SMALL_EVAL, "medium": MEDIUM_EVAL}


def run(stage_names: list[str]) -> None:
    skills = load_skill_lexicon()
    print(f"Skill lexicon: {len(skills):,} terms")

    resumes = load_resumes()
    jobs = load_human_jobs()
    labeled_jobs = int(jobs["category"].notna().sum())
    print(f"Resumes: {len(resumes):,} | Human-written jobs: {len(jobs):,} | Title-labeled jobs: {labeled_jobs:,}")

    matcher = ResumeJobMatcher(skills)
    reports = []
    for name in stage_names:
        report = evaluate_stage(matcher, resumes, jobs, STAGES[name], seed=RANDOM_SEED)
        reports.append(report)
        print(
            f"{report.stage}: top-1 {report.top1_accuracy}% | "
            f"top-{report.top_k} {report.topk_accuracy}% | "
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
        help="small checks obvious profile-to-job pairs; medium mixes more occupations.",
    )
    args = parser.parse_args()
    names = ["small", "medium"] if args.stage == "both" else [args.stage]
    run(names)


if __name__ == "__main__":
    main()
