"""Write JSON summary and a screenshot-ready project-review HTML report."""

import json
from html import escape
from pathlib import Path

from matcher.config import BODY_WEIGHT, REPORTS_DIR, SKILL_WEIGHT, TITLE_WEIGHT
from matcher.evaluation import RankedJob, ResumeResult, StageReport

PROJECT_REVIEW_HTML = "project-review.html"

_SAMPLE_LABELS: dict[str, str] = {
    "small": "Small",
    "medium": "Larger",
}

_STYLES = """
    :root {
      --bg: #eef2f6;
      --card: #ffffff;
      --ink: #0f172a;
      --muted: #475569;
      --line: #e2e8f0;
      --header: #0f172a;
      --accent: #1d4ed8;
      --green: #15803d;
      --green-bg: #dcfce7;
      --red: #b91c1c;
      --red-bg: #fee2e2;
      --amber: #b45309;
      --row-alt: #f8fafc;
      --highlight: #dbeafe;
      --shadow: 0 1px 2px rgba(15, 23, 42, 0.06), 0 8px 24px rgba(15, 23, 42, 0.04);
    }
    * { box-sizing: border-box; }
    html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: Inter, "Segoe UI", Roboto, system-ui, sans-serif;
      font-size: 17px;
      line-height: 1.55;
    }
    .page { max-width: 1120px; margin: 0 auto; padding: 24px 28px 36px; }
    header.hero {
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 16px;
      box-shadow: var(--shadow);
      padding: 22px 28px 18px;
      margin-bottom: 12px;
      border-top: 6px solid var(--accent);
    }
    h1 {
      margin: 0 0 8px;
      font-size: 28px;
      line-height: 1.2;
      letter-spacing: -0.02em;
      font-weight: 700;
    }
    .subtitle { margin: 0; color: var(--muted); font-size: 18px; }
    .section-tag {
      display: inline-block;
      font-size: 12px;
      font-weight: 700;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      color: var(--accent);
      margin-bottom: 8px;
    }
    section.card {
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 16px;
      box-shadow: var(--shadow);
      padding: 16px 22px 18px;
      margin-bottom: 12px;
    }
    h2 { margin: 0 0 8px; font-size: 20px; letter-spacing: -0.01em; }
    h3 { margin: 14px 0 6px; font-size: 16px; font-weight: 600; }
    p { margin: 0 0 12px; }
    .lead { color: var(--muted); margin-bottom: 16px; }
    .interpret {
      background: #f8fafc;
      border-left: 4px solid var(--accent);
      padding: 12px 16px;
      margin: 14px 0 4px;
      font-size: 16px;
    }
    ul.clean { margin: 0; padding-left: 22px; }
    ul.clean li { margin: 0 0 10px; }
    ul.clean li:last-child { margin-bottom: 0; }
    code {
      font-family: ui-monospace, "Cascadia Code", Consolas, monospace;
      font-size: 0.92em;
      background: #f1f5f9;
      padding: 1px 6px;
      border-radius: 6px;
    }
    .defs { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; }
    .def {
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 16px 18px;
      background: #f8fafc;
    }
    .def strong { display: block; font-size: 16px; margin-bottom: 6px; }
    .def span { color: var(--muted); font-size: 15.5px; }
    .outcome { margin: 14px 0 0; font-weight: 600; }
    .kpis {
      display: grid;
      grid-template-columns: repeat(5, 1fr);
      gap: 12px;
      margin: 16px 0 8px;
    }
    .kpi {
      background: #f8fafc;
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 14px 12px 12px;
      text-align: center;
    }
    .kpi .value {
      display: block;
      font-size: 32px;
      font-weight: 700;
      letter-spacing: -0.03em;
      line-height: 1.1;
      color: var(--accent);
    }
    .kpi .value.green { color: var(--green); }
    .kpi .value.ink { color: var(--ink); }
    .kpi .label {
      display: block;
      margin-top: 6px;
      color: var(--muted);
      font-size: 13.5px;
      font-weight: 600;
    }
    table { width: 100%; border-collapse: collapse; margin-top: 8px; font-size: 16px; }
    th, td {
      text-align: left;
      padding: 8px 10px;
      border-bottom: 1px solid var(--line);
      vertical-align: middle;
    }
    th {
      background: var(--header);
      color: #f8fafc;
      font-size: 13.5px;
      font-weight: 700;
      letter-spacing: 0.04em;
      text-transform: uppercase;
    }
    th.num, td.num { text-align: right; font-variant-numeric: tabular-nums; }
    th.speak {
      text-transform: none;
      letter-spacing: 0;
      font-size: 14.5px;
      font-weight: 650;
      line-height: 1.35;
    }
    th.speak.center { text-align: center; }
    th.speak span { display: block; margin-top: 3px; font-weight: 500; font-size: 12px; color: #cbd5e1; }
    td .sub { display: block; margin-top: 2px; color: var(--muted); font-size: 13px; font-weight: 500; }
    tbody tr:nth-child(even) { background: var(--row-alt); }
    tbody tr:nth-child(odd) { background: #fff; }
    tr.highlight td { background: var(--highlight); font-weight: 700; }
    tr.highlight td:first-child { box-shadow: inset 4px 0 0 var(--accent); }
    .pct.good { color: var(--green); font-weight: 700; }
    .pct.mid { color: var(--amber); font-weight: 700; }
    .pct.low { color: var(--red); font-weight: 700; }
    .pill {
      display: inline-block;
      font-weight: 700;
      font-size: 14px;
      padding: 3px 10px;
      border-radius: 999px;
    }
    .pill.same, .pill.done { color: var(--green); background: var(--green-bg); }
    .pill.different { color: var(--red); background: var(--red-bg); }
    .pill.partial { color: var(--amber); background: #fef3c7; }
    .pill.later { color: #1e3a8a; background: #dbeafe; }
    .progress {
      height: 12px;
      background: #e2e8f0;
      border-radius: 999px;
      overflow: hidden;
      min-width: 120px;
    }
    .progress > span {
      display: block;
      height: 100%;
      background: var(--accent);
      border-radius: 999px;
    }
    .progress.good > span { background: var(--green); }
    .progress.mid > span { background: var(--amber); }
    .caption { margin: 10px 0 0; color: var(--muted); font-size: 14.5px; }
    .skill-gap-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
      margin-top: 14px;
    }
    .skill-box {
      border-radius: 12px;
      padding: 14px 16px;
      font-size: 15.5px;
      line-height: 1.45;
    }
    .skill-box strong { display: block; margin-bottom: 6px; font-size: 14px; text-transform: uppercase; letter-spacing: 0.04em; }
    .skill-box.match { background: var(--green-bg); border: 1px solid #86efac; color: #14532d; }
    .skill-box.gap { background: var(--red-bg); border: 1px solid #fca5a5; color: #7f1d1d; }
    .skill-example {
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 18px 20px;
      margin-top: 16px;
      background: #fff;
    }
    .skill-example h4 { margin: 0 0 8px; font-size: 16px; }
    .evidence {
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 16px;
      margin-top: 16px;
      background: #fff;
    }
    .evidence-head {
      display: flex;
      flex-wrap: wrap;
      gap: 6px 18px;
      align-items: baseline;
      margin-bottom: 4px;
      font-size: 16px;
    }
    .evidence-head .badge { font-weight: 700; font-size: 17px; }
    .yes { color: var(--green); font-weight: 700; }
    .no { color: var(--red); font-weight: 700; }
    .evidence table { margin-top: 8px; font-size: 15.5px; }
    .evidence th, .evidence td { padding: 9px 12px; }
    .parts { margin: 10px 0 0; font-size: 15.5px; line-height: 1.5; }
    .formula {
      margin: 8px 0 0;
      padding: 16px 18px;
      border-radius: 12px;
      background: #0f172a;
      color: #f8fafc;
      font-family: ui-monospace, "Cascadia Code", Consolas, monospace;
      font-size: 18px;
      line-height: 1.55;
    }
    .formula span { color: #93c5fd; }
    .plain {
      background: #f8fafc;
      border-left: 4px solid var(--accent);
      padding: 12px 16px;
      margin: 0 0 16px;
    }
    details.backup { margin-top: 8px; }
    details.backup > summary {
      cursor: pointer;
      list-style: none;
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 16px;
      box-shadow: var(--shadow);
      padding: 18px 24px;
      font-size: 18px;
      font-weight: 700;
    }
    details.backup > summary::-webkit-details-marker { display: none; }
    details.backup > summary::before { content: "▸ "; color: var(--accent); }
    details.backup[open] > summary::before { content: "▾ "; }
    details.backup[open] > summary { border-radius: 16px 16px 0 0; margin-bottom: 0; }
    details.backup .backup-body { padding-top: 16px; }
    section.card.bottom {
      background: #0f172a;
      color: #e2e8f0;
      border-color: #334155;
    }
    section.card.bottom h2 { color: #f8fafc; }
    section.card.bottom .plain { background: #1e293b; color: #f8fafc; border-left-color: #93c5fd; }
    section.card.bottom p, section.card.bottom li { color: #e2e8f0; font-size: 17px; line-height: 1.55; }
    section.card.bottom strong { color: #93c5fd; font-weight: 700; }
    @media (max-width: 900px) {
      .defs, .kpis, .skill-gap-grid { grid-template-columns: 1fr; }
      .page { padding: 20px 16px 32px; }
      h1 { font-size: 28px; }
      section.card, header.hero { padding: 20px 18px; }
    }
    @media print {
      body { background: #fff; }
      .page { max-width: none; padding: 0; }
      header.hero, section.card { box-shadow: none; break-inside: avoid; page-break-inside: avoid; }
      .evidence, .skill-example { break-inside: avoid; page-break-inside: avoid; }
      .sheet-start { break-before: page; page-break-before: always; }
    }
"""


def _format_skill_list(skills: list[str]) -> str:
    if not skills:
        return "None"
    return ", ".join(escape(skill) for skill in skills)


def _comparison_row(stage: StageReport, method: str) -> dict | None:
    for row in stage.comparisons:
        if row["method"] == method:
            return row
    return None


def _skill_gap_boxes(matching: list[str], gaps: list[str]) -> str:
    return f"""
      <div class="skill-gap-grid">
        <div class="skill-box match">
          <strong>Matching skills</strong>
          {_format_skill_list(matching)}
        </div>
        <div class="skill-box gap">
          <strong>Skill gaps</strong>
          {_format_skill_list(gaps)}
        </div>
      </div>
"""


def write_reports(stages: list[StageReport], directory: Path = REPORTS_DIR) -> tuple[Path, Path]:
    directory.mkdir(parents=True, exist_ok=True)
    payload = {"stages": [stage.to_dict() for stage in stages]}
    json_path = directory / "accuracy.json"
    html_path = directory / PROJECT_REVIEW_HTML
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    html_path.write_text(_render_html(stages), encoding="utf-8")
    return json_path, html_path


def _render_html(stages: list[StageReport]) -> str:
    top_k = stages[0].top_k if stages else 3
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Explainable NLP Approach for Resume–Job Matching and Skill Gap Analysis</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet" />
  <style>{_STYLES}</style>
</head>
<body>
  <div class="page">
    {_overview_header()}
    {_progress_section(stages)}
    {_method_section(top_k)}
    {_results_section(stages)}
    {_skill_gap_example(stages)}
    {_limitations_section()}
  </div>
</body>
</html>
"""


def _overview_header() -> str:
    return """
    <header class="hero">
      <p class="section-tag">MCA Second Review</p>
      <h1>Explainable NLP approach for resume–job matching and skill gap analysis</h1>
      <p class="subtitle">Given a resume, the system orders software jobs and lists matching skills and skill gaps.</p>
    </header>
"""


def _outcome_rows() -> list[tuple[str, str, str, str]]:
    return [
        ("Find the skills in a resume and a job", "Completed", "done",
         "Public resumes and human-written jobs. The system keeps terms that mark a software role, such as Python, Docker, or wireframes."),
        ("Match a resume to jobs", "Completed", "done",
         "Frontend, Backend, UX, and Infrastructure engineer. Each resume is scored against each job, then jobs are sorted from the closest fit to the weakest."),
        ("Give every pair a score", "Completed", "done",
         "The score used for the ranking is shown below. A second, meaning-based score is reported beside it."),
        ("Explain what is missing", "Completed", "done",
         "For the top job, the page lists matching skills and skill gaps."),
        ("Interactive application", "Remaining", "later",
         "Still open: upload a resume and a job, then show the score and the skill gaps."),
    ]


def _small_sample_line(stages: list[StageReport]) -> str:
    small = next((stage for stage in stages if stage.stage == "small"), None)
    if small is None:
        return ""
    match = _comparison_row(small, "Blend")
    semantic = _comparison_row(small, "Semantic matching")
    if not match or not semantic:
        return ""
    return (
        "<p class=\"interpret\">On the small sample the TF-IDF match score reached "
        f"{_percent(match['top1_accuracy'])} best match; semantic was "
        f"{_percent(semantic['top1_accuracy'])}.</p>"
    )


def _progress_section(stages: list[StageReport]) -> str:
    body = "\n".join(
        f"<tr><td>{name}</td>"
        f'<td><span class="pill {tone}">{status}</span></td>'
        f"<td>{note}</td></tr>"
        for name, status, tone, note in _outcome_rows()
    )
    return f"""
    <section class="card">
      <p class="section-tag">Progress</p>
      <h2>Objectives and current status</h2>
      <p class="lead">Four objectives are completed. The interactive prototype is the one item still open.</p>
      <table>
        <thead>
          <tr>
            <th>Proposed outcome</th>
            <th>Status</th>
            <th>In this build</th>
          </tr>
        </thead>
        <tbody>{body}</tbody>
      </table>
      {_small_sample_line(stages)}
    </section>
"""


def _method_section(top_k: int) -> str:
    body_pct = f"{BODY_WEIGHT * 100:.0f}%"
    title_pct = f"{TITLE_WEIGHT * 100:.0f}%"
    skill_pct = f"{SKILL_WEIGHT * 100:.0f}%"
    return f"""
    <section class="card sheet-start">
      <p class="section-tag">Method</p>
      <h2>How a resume is scored</h2>
      <p class="formula">match score = <span>{body_pct}</span> body TF-IDF + <span>{title_pct}</span> title TF-IDF + <span>{skill_pct}</span> skill coverage</p>
      <p class="caption">{body_pct} body, {title_pct} title, {skill_pct} skill. Body and title are TF-IDF cosines. Skill coverage is the share of the job’s skill terms found on the resume. This score orders the jobs.</p>
      <ul class="clean">
        <li><strong>Data.</strong> Public resumes and human-written jobs, limited to Frontend, Backend, UX, and Infrastructure engineer.</li>
        <li><strong>Semantic score.</strong> Cosine of sentence embeddings. Comparison only; it is not added into the match score.</li>
        <li><strong>Evaluation.</strong> Best match, Top-{top_k}, and MRR. Same IT role counts as correct.</li>
      </ul>
    </section>
"""


def _percent(value: float) -> str:
    if float(value).is_integer():
        return f"{int(value)}%"
    return f"{value}%"


def _results_section(stages: list[StageReport]) -> str:
    rows = []
    for stage in stages:
        label = _SAMPLE_LABELS.get(stage.stage)
        if label is None:
            continue
        match = _comparison_row(stage, "Blend")
        semantic = _comparison_row(stage, "Semantic matching")
        if not match or not semantic:
            continue
        rows.append(
            f"<tr><td>{escape(label)}"
            f"<span class=\"sub\">{stage.resumes} resumes, {stage.jobs} jobs</span></td>"
            f"<td class=\"num\">{_percent(match['top1_accuracy'])}</td>"
            f"<td class=\"num\">{_percent(semantic['top1_accuracy'])}</td>"
            f"<td class=\"num\">{match['mrr']:.3f}</td>"
            f"<td class=\"num\">{semantic['mrr']:.3f}</td></tr>"
        )
    if not rows:
        return ""
    return f"""
    <section class="card">
      <p class="section-tag">Results</p>
      <h2>Match score and semantic score</h2>
      <table>
        <thead>
          <tr>
            <th>Sample</th>
            <th class="num">Match Best</th>
            <th class="num">Semantic Best</th>
            <th class="num">Match MRR</th>
            <th class="num">Semantic MRR</th>
          </tr>
        </thead>
        <tbody>{"".join(rows)}</tbody>
      </table>
      <p class="interpret">TF-IDF is stronger on the small sample; on the larger sample best match is tied, and TF-IDF stays slightly ahead on MRR.</p>
    </section>
"""


def _pretty_skills(skills: list[str]) -> list[str]:
    names = {
        "aws": "AWS",
        "css": "CSS",
        "html": "HTML",
        "sql": "SQL",
        "ui": "UI",
        "ux": "UX",
    }
    pretty = []
    for skill in _shown_skills(skills):
        pretty.append(names.get(skill, skill[:1].upper() + skill[1:]))
    return pretty


def _skill_gap_example(stages: list[StageReport]) -> str:
    chosen: tuple[tuple[int, int], ResumeResult, RankedJob, list[str], list[str]] | None = None
    for stage in stages:
        for result in stage.results:
            if result.resume_category != "Infrastructure engineer" or not result.top_jobs:
                continue
            job = result.top_jobs[0]
            matching = _pretty_skills(job.matching_skills)
            gaps = _pretty_skills(job.skill_gaps)
            if not matching and not gaps:
                continue
            rank = (1 if job.correct else 0, len(matching) + len(gaps))
            if chosen is None or rank > chosen[0]:
                chosen = (rank, result, job, matching, gaps)
    if chosen is None:
        return ""
    _, result, job, matching, gaps = chosen
    same = "same role" if job.correct else "different role"
    return f"""
    <section class="card sheet-start">
      <p class="section-tag">Skill gap</p>
      <h2>Infrastructure engineer example</h2>
      <p>Resume {escape(result.resume_id)} is an Infrastructure engineer. The first job is {escape(job.title.strip())} ({same}). Match score {job.score}.</p>
      {_skill_gap_boxes(matching, gaps)}
    </section>
"""


def _limitations_section() -> str:
    return """
    <section class="card">
      <p class="section-tag">Limitations and next step</p>
      <h2>What this check does not show</h2>
      <p>Each role has only a small number of resumes, and the role labels come from phrases in the title or the resume.</p>
      <p>Next: a basic interactive prototype where a resume and a job are uploaded and the page shows the score and the skill gaps.</p>
    </section>
"""


def _shown_skills(skills: list[str]) -> list[str]:
    noise = {
        "successful", "focus", "focused", "skilled", "organization",
        "install", "installing", "installed", "installation",
        "developer", "developers", "methodologies", "methodology",
        "maintenance", "maintaining", "administration", "updates",
        "interactive", "systems administrator", "system administrator",
        "resources", "variety", "vision", "user experience",
        "departments", "february", "print", "accurate", "networking",
        "understand", "administrator", "effectively", "media", "sessions",
    }
    return [skill for skill in skills if skill not in noise]


def load_stages_from_json(path: Path) -> list[StageReport]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    stages: list[StageReport] = []
    for stage in payload["stages"]:
        results: list[ResumeResult] = []
        for item in stage["results"]:
            top_jobs = [RankedJob(**job) for job in item["top_jobs"]]
            results.append(
                ResumeResult(
                    resume_id=item["resume_id"],
                    resume_category=item["resume_category"],
                    top1_correct=item["top1_correct"],
                    topk_correct=item["topk_correct"],
                    top_jobs=top_jobs,
                )
            )
        stages.append(
            StageReport(
                stage=stage["stage"],
                resumes=stage["resumes"],
                jobs=stage["jobs"],
                categories=stage["categories"],
                top1_accuracy=stage["top1_accuracy"],
                topk_accuracy=stage["topk_accuracy"],
                top_k=stage["top_k"],
                by_category=stage["by_category"],
                results=results,
                comparisons=stage.get("comparisons", []),
                mrr=stage.get("mrr", 0.0),
            )
        )
    return stages


def refresh_html_from_json(
    json_path: Path = REPORTS_DIR / "accuracy.json",
    html_path: Path | None = None,
) -> Path:
    """Regenerate project-review.html from accuracy.json without re-running evaluation."""
    html_path = html_path or json_path.parent / PROJECT_REVIEW_HTML
    stages = load_stages_from_json(json_path)
    html_path.write_text(_render_html(stages), encoding="utf-8")
    return html_path

