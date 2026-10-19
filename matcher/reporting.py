"""Write a JSON summary and a single-page HTML report for screenshots."""

import json
from html import escape
from pathlib import Path

from matcher.config import REPORTS_DIR
from matcher.evaluation import StageReport


def _accuracy_tone(value: float) -> str:
    if value >= 70:
        return "good"
    if value >= 40:
        return "mid"
    return "low"


def write_reports(stages: list[StageReport], directory: Path = REPORTS_DIR) -> tuple[Path, Path]:
    directory.mkdir(parents=True, exist_ok=True)
    payload = {"stages": [stage.to_dict() for stage in stages]}
    json_path = directory / "accuracy.json"
    html_path = directory / "accuracy.html"
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    html_path.write_text(_render_html(stages), encoding="utf-8")
    return json_path, html_path


def _render_html(stages: list[StageReport]) -> str:
    sections = "\n".join(_stage_section(stage) for stage in stages)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Resume matcher accuracy</title>
  <style>
    body {{ font-family: Georgia, serif; margin: 32px auto; max-width: 1100px; color: #1c1917; background: #fafaf9; }}
    h1 {{ font-size: 28px; margin-bottom: 4px; }}
    h2 {{ font-size: 20px; margin-top: 36px; }}
    p, td, th {{ font-family: "Segoe UI", sans-serif; font-size: 14px; }}
    .muted {{ color: #57534e; }}
    .stats {{ display: flex; gap: 16px; margin: 12px 0 20px; }}
    .stat {{ background: white; border: 1px solid #e7e5e4; padding: 12px 16px; min-width: 140px; }}
    .stat b {{ display: block; font-size: 28px; font-family: "Segoe UI", sans-serif; }}
    .good {{ color: #166534; }}
    .mid {{ color: #a16207; }}
    .low {{ color: #991b1b; }}
    table {{ width: 100%; border-collapse: collapse; background: white; }}
    th, td {{ border-bottom: 1px solid #e7e5e4; text-align: left; padding: 8px 10px; vertical-align: top; }}
    th {{ font-size: 12px; letter-spacing: 0.04em; text-transform: uppercase; color: #57534e; }}
    .hit {{ color: #166534; font-weight: 600; }}
    .miss {{ color: #991b1b; font-weight: 600; }}
  </style>
</head>
<body>
  <h1>Resume to job accuracy</h1>
  <p class="muted">A match is correct when the ranked job title belongs to the same occupation as the resume category. Source: snehaanbhawal/resume-dataset and human-written postings from avinashmynampati/human-vs-fake-vs-ai-generated-job-descriptions.</p>
  {sections}
</body>
</html>
"""


def _stage_section(stage: StageReport) -> str:
    tone = _accuracy_tone(stage.top1_accuracy)
    category_rows = "\n".join(
        "<tr>"
        f"<td>{escape(row['category'])}</td>"
        f"<td>{row['resumes']}</td>"
        f"<td class=\"{_accuracy_tone(row['top1_accuracy'])}\">{row['top1_accuracy']}%</td>"
        f"<td>{row['topk_accuracy']}%</td>"
        "</tr>"
        for row in stage.by_category
    )
    example_rows = []
    for item in stage.results:
        top = item.top_jobs[0]
        mark = "hit" if item.top1_correct else "miss"
        label = "Correct" if item.top1_correct else "Miss"
        example_rows.append(
            "<tr>"
            f"<td>{escape(item.resume_id)}</td>"
            f"<td>{escape(item.resume_category)}</td>"
            f"<td>{escape(top.title)}</td>"
            f"<td>{escape(top.category)}</td>"
            f"<td>{top.score}</td>"
            f"<td class=\"{mark}\">{label}</td>"
            "</tr>"
        )
    return f"""
  <h2>{escape(stage.stage.title())} dataset</h2>
  <p class="muted">{stage.resumes} resumes ranked against {stage.jobs} labeled jobs across {len(stage.categories)} occupations. Top-{stage.top_k} counts a resume as correct if any of the first {stage.top_k} jobs shares its category.</p>
  <div class="stats">
    <div class="stat"><b class="{tone}">{stage.top1_accuracy}%</b>Top-1 accuracy</div>
    <div class="stat"><b>{stage.topk_accuracy}%</b>Top-{stage.top_k} accuracy</div>
    <div class="stat"><b>{stage.resumes}</b>Resumes</div>
    <div class="stat"><b>{stage.jobs}</b>Jobs</div>
  </div>
  <table>
    <thead><tr><th>Occupation</th><th>Resumes</th><th>Top-1</th><th>Top-{stage.top_k}</th></tr></thead>
    <tbody>{category_rows}</tbody>
  </table>
  <h2>{escape(stage.stage.title())} resume checks</h2>
  <table>
    <thead><tr><th>Resume</th><th>Profile</th><th>Top job</th><th>Job occupation</th><th>Score</th><th>Result</th></tr></thead>
    <tbody>{"".join(example_rows)}</tbody>
  </table>
"""
