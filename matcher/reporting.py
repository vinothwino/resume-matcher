"""Write JSON summary and a screenshot-ready project-review HTML report."""

import json
from html import escape
from pathlib import Path

from matcher.config import BODY_WEIGHT, REPORTS_DIR, SKILL_WEIGHT, TITLE_WEIGHT
from matcher.evaluation import RankedJob, ResumeResult, StageReport

PROJECT_REVIEW_HTML = "project-review.html"

_EXPERIMENT_TITLES: dict[str, str] = {
    "small": "Controlled sample",
    "medium": "Broader sample",
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
    .page { max-width: 1120px; margin: 0 auto; padding: 40px 36px 56px; }
    header.hero {
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 16px;
      box-shadow: var(--shadow);
      padding: 32px 36px 28px;
      margin-bottom: 20px;
      border-top: 6px solid var(--accent);
    }
    h1 {
      margin: 0 0 8px;
      font-size: 34px;
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
      padding: 28px 32px 30px;
      margin-bottom: 20px;
    }
    h2 { margin: 0 0 14px; font-size: 22px; letter-spacing: -0.01em; }
    h3 { margin: 22px 0 8px; font-size: 17px; font-weight: 600; }
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
      padding: 12px 14px;
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
    }
"""


def _format_skill_list(skills: list[str]) -> str:
    if not skills:
        return "None"
    return ", ".join(escape(skill) for skill in skills)


def _accuracy_tone(value: float) -> str:
    if value >= 70:
        return "good"
    if value >= 40:
        return "mid"
    return "low"


def _stage_by_name(stages: list[StageReport], name: str) -> StageReport | None:
    for stage in stages:
        if stage.stage == name:
            return stage
    return None


def _comparison_row(stage: StageReport, method: str) -> dict | None:
    for row in stage.comparisons:
        if row["method"] == method:
            return row
    return None


def _experiment_lead(stage: StageReport) -> str:
    roles = ", ".join(stage.categories)
    if stage.stage == "small":
        size = "2 resumes and 2 jobs in each IT role"
    elif stage.stage == "medium":
        size = "3 resumes and 5 jobs in each IT role"
    else:
        size = "IT roles only"
    return f"IT / software sample only — {roles}. {size}. {stage.resumes} resumes × {stage.jobs} jobs."


def _experiment_interpretation(stage: StageReport) -> str:
    baseline = _comparison_row(stage, "TF-IDF cosine")
    semantic = _comparison_row(stage, "Semantic matching")
    blend = _comparison_row(stage, "Blend")
    if not baseline or not semantic or not blend:
        return ""
    return (
        f"<strong>Interpretation:</strong> TF-IDF cosine best match is {baseline['top1_accuracy']}%. "
        f"Semantic matching, the embedding cosine, is {semantic['top1_accuracy']}%. "
        f"The reported rank is the blend at {blend['top1_accuracy']}% best match "
        f"(MRR {blend['mrr']:.3f})."
    )


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
    experiments = "".join(
        _experiment_section(stage)
        for stage in stages
        if stage.stage in _EXPERIMENT_TITLES
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Resume–job matcher — MCA Second Review</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet" />
  <style>{_STYLES}</style>
</head>
<body>
  <div class="page">
    {_overview_header()}
    {_progress_section()}
    {_proposal_section()}
    {_method_section()}
    {_baseline_blend_summary(stages, top_k)}
    {experiments}
    {_skill_gap_examples_section(stages)}
    {_limitations_next_steps(stages)}
  </div>
</body>
</html>
"""


def _overview_header() -> str:
    return """
    <header class="hero">
      <p class="section-tag">MCA Second Review</p>
      <h1>Resume–job matching for IT and software roles</h1>
      <p class="subtitle">Second review of the proposed study: frontend, backend, UX, and infrastructure-engineer resumes and jobs, ranked by a TF-IDF match score, compared with semantic matching, and explained with skill gaps.</p>
    </header>
"""


def _progress_bar(percent: int) -> str:
    tone = "good" if percent >= 70 else "mid" if percent >= 40 else ""
    return (
        f'<div class="progress {tone}"><span style="width:{percent}%"></span></div>'
    )


def _outcome_rows() -> list[tuple[str, str, str, str]]:
    return [
        ("Automated extraction of skills and qualifications", "Completed", "done",
         "Role-distinctive terms are taken from resumes outside the scored sample and matched on the resume and the job."),
        ("Candidate–job matching with NLP", "Completed", "done",
         "Each pair receives one match score from TF-IDF cosine and skill coverage, and a separate semantic score."),
        ("Match score and ranking", "Completed", "done",
         "Jobs are ordered by the match score. Best match, top-3, and mean reciprocal rank are reported."),
        ("Skill-gap identification", "Completed", "done",
         "Each ranked job lists skills present on the resume and skills required by the job that the resume does not list."),
        ("Interactive application", "Remaining", "later",
         "The proposed React/Next.js interface is not part of this review build."),
    ]


def _progress_section() -> str:
    body = "\n".join(
        f"<tr><td>{name}</td>"
        f'<td><span class="pill {tone}">{status}</span></td>'
        f"<td>{note}</td></tr>"
        for name, status, tone, note in _outcome_rows()
    )
    return f"""
    <section class="card">
      <p class="section-tag">1. Progress</p>
      <h2>Status of the proposed outcomes</h2>
      <p class="lead">Four of the five proposed outcomes are implemented. The interactive application remains.</p>
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
    </section>
"""


def _proposal_section() -> str:
    rows = [
        ("Research type", "Exploratory + analytical", "Aligned", "done",
         "Two IT samples, with best match, top-3, and mean reciprocal rank."),
        ("Data source", "Public resume and job-description datasets", "Aligned", "done",
         "Public resume corpus and human-written job postings."),
        ("Data collection", "Dataset load, NLP preprocessing, skill extraction, features", "Aligned", "done",
         "Text cleaning, TF-IDF features, sentence embeddings, and skill terms."),
        ("Sample", "IT / software roles", "Aligned", "done",
         "Frontend, backend, UX, and infrastructure engineer."),
        ("Tools", "Python, Pandas, NumPy, Scikit-learn, NLP/embedding libraries, React/Next.js", "Partial", "partial",
         "Python, Pandas, NumPy, Scikit-learn, and sentence-transformers. React/Next.js is not built."),
        ("Analysis", "NLP, TF-IDF/Cosine Similarity, Semantic Matching, ML-based comparison, Skill Gap Analysis", "Aligned", "done",
         "Each item is defined in the methodology and reported below."),
    ]
    body = "\n".join(
        f"<tr><td>{component}</td><td>{proposed}</td>"
        f'<td><span class="pill {tone}">{status}</span></td>'
        f"<td>{evidence}</td></tr>"
        for component, proposed, status, tone, evidence in rows
    )
    return f"""
    <section class="card">
      <p class="section-tag">2. Proposed approach</p>
      <h2>Alignment with the proposed approach</h2>
      <table>
        <thead>
          <tr>
            <th>Component</th>
            <th>Proposed approach</th>
            <th>Status</th>
            <th>This build</th>
          </tr>
        </thead>
        <tbody>{body}</tbody>
      </table>
    </section>
"""


def _alignment_section() -> str:
    return f"""
    <section class="card">
      <p class="section-tag">3. Implementation</p>
      <h2>Implementation summary</h2>
      <ul class="clean">
        <li><strong>Skill extraction:</strong> Distinctive occupation terms are mined from resumes that are not in the scored sample, then matched on resume and job text.</li>
        <li><strong>Ranking:</strong> blend = {BODY_WEIGHT:.2f} × cosine(TF-IDF resume, job description) + {TITLE_WEIGHT:.2f} × cosine(TF-IDF resume, job title) + {SKILL_WEIGHT:.2f} × skill coverage.</li>
        <li><strong>Skill gaps:</strong> Each ranked job lists skills the resume already has and skills the job asks for that the resume lacks.</li>
        <li><strong>Left for the final review:</strong> An interactive page where a recruiter or candidate can paste a resume and a job.</li>
      </ul>
    </section>
"""


def _method_section() -> str:
    return f"""
    <section class="card">
      <p class="section-tag">3. Methodology</p>
      <h2>Methodology</h2>
      <h3>Data and sample</h3>
      <p>Resumes and human-written job descriptions are taken from public datasets. Records are labeled frontend, backend, UX, or infrastructure engineer from role phrases in the resume or the job title. The controlled sample uses 2 resumes and 2 jobs in each role. The broader sample uses 3 resumes and 5 jobs in each role.</p>
      <h3>NLP and skill extraction</h3>
      <p>Text is lower-cased and reduced to word tokens, with English stop words removed. Skill terms are phrases that occur more often inside one IT role than outside it. Resumes that are scored are excluded from this extraction. Skill coverage is the number of skill terms found on both the resume and the job, divided by the number of skill terms on the job.</p>
      <h3>TF-IDF match score</h3>
      <p>The match score is TF-IDF cosine on the job description and the job title, combined with skill coverage. Jobs are ranked by this score.</p>
      <p class="formula">score = <span>{BODY_WEIGHT:.2f}</span> × cosine(TF-IDF resume, job description)<br>
      + <span>{TITLE_WEIGHT:.2f}</span> × cosine(TF-IDF resume, job title)<br>
      + <span>{SKILL_WEIGHT:.2f}</span> × skill coverage</p>
      <h3>Semantic matching</h3>
      <p>Semantic matching is the cosine similarity between sentence embeddings of the resume and of the job title plus description. The model is all-MiniLM-L6-v2. Long documents are split into sections, embedded, and averaged, so the score is not limited to the opening lines. This score is compared with the match score. It is not added into the formula above.</p>
      <h3>Evaluation</h3>
      <p>A job is correct when its IT role equals the resume&rsquo;s IT role. Best match means rank 1 is correct. Top-3 means a correct role appears among the first three. Mean reciprocal rank is 1 divided by the rank of the first correct role, averaged over resumes.</p>
    </section>
"""


def _metrics_section(top_k: int, small: StageReport | None) -> str:
    example = _worked_example_html(small)
    return f"""
    <section class="card">
      <p class="section-tag">5. Evaluation</p>
      <h2>Evaluation metrics</h2>
      <div class="defs">
        <div class="def">
          <strong>Best match</strong>
          <span>The rank-1 job&rsquo;s occupation equals the resume&rsquo;s occupation.</span>
        </div>
        <div class="def">
          <strong>Found in the first {top_k}</strong>
          <span>At least one of ranks 1 through {top_k} has the same occupation as the resume.</span>
        </div>
        <div class="def">
          <strong>Mean reciprocal rank (MRR)</strong>
          <span>One divided by the rank of the first correct occupation, averaged over resumes.</span>
        </div>
      </div>
      {example}
    </section>
"""


def _worked_example_html(small: StageReport | None) -> str:
    if not small:
        return ""
    target = next((r for r in small.results if len(r.top_jobs) >= 3), None)
    if not target:
        return ""
    rows = []
    for index, job in enumerate(target.top_jobs[:3], start=1):
        pill = "same" if job.correct else "different"
        label = "Same" if job.correct else "Different"
        rows.append(
            f"<tr><td>{index}</td><td>{escape(job.title)}</td><td>{escape(job.category)}</td>"
            f'<td class="num">{job.score}</td>'
            f'<td><span class="pill {pill}">{label}</span></td></tr>'
        )
    rank1 = target.top_jobs[0]
    return f"""
      <h3>Worked example (explainability)</h3>
      <p class="lead">Resume {escape(target.resume_id)}, profile {escape(target.resume_category)} — top 3 jobs by the blend.</p>
      <table>
        <thead>
          <tr>
            <th>Rank</th><th>Job title</th><th>Occupation</th>
            <th class="num">Score</th><th>vs profile</th>
          </tr>
        </thead>
        <tbody>{"".join(rows)}</tbody>
      </table>
      <p class="outcome">Best match: {"no" if not target.top1_correct else "yes"}. Found in the first {small.top_k}: {"yes" if target.topk_correct else "no"}.</p>
      <p class="caption">Skill gap for rank-1 job <em>{escape(rank1.title)}</em>. Blend score {rank1.score}.</p>
      {_skill_gap_boxes(rank1.matching_skills, rank1.skill_gaps)}
"""


def _baseline_blend_summary(stages: list[StageReport], top_k: int) -> str:
    rows = []
    for stage in stages:
        if stage.stage not in _EXPERIMENT_TITLES:
            continue
        label = _EXPERIMENT_TITLES[stage.stage]
        semantic = _comparison_row(stage, "Semantic matching")
        blend = _comparison_row(stage, "Blend")
        if not semantic or not blend:
            continue
        rows.append(
            f"<tr><td>{escape(label)}</td>"
            f"<td class=\"num\">{blend['top1_accuracy']}%</td>"
            f"<td class=\"num\">{semantic['top1_accuracy']}%</td>"
            f"<td class=\"num\">{blend['mrr']:.3f}</td>"
            f"<td class=\"num\">{semantic['mrr']:.3f}</td></tr>"
        )
    if not rows:
        return ""
    return f"""
    <section class="card">
      <p class="section-tag">4. Results</p>
      <h2>Comparison of the match score and semantic matching</h2>
      <p class="lead">The match score is the ranking score defined above. Semantic matching is the embedding cosine on the same pairs.</p>
      <table>
        <thead>
          <tr>
            <th>Sample</th>
            <th class="num">Match score, best match</th>
            <th class="num">Semantic, best match</th>
            <th class="num">Match score, MRR</th>
            <th class="num">Semantic, MRR</th>
          </tr>
        </thead>
        <tbody>{"".join(rows)}</tbody>
      </table>
    </section>
"""


def _experiment_section(stage: StageReport) -> str:
    title = _EXPERIMENT_TITLES.get(stage.stage, stage.stage.title())
    category_rows = "\n".join(
        f"<tr><td>{escape(row['category'])}</td><td class=\"num\">{row['resumes']}</td>"
        f"<td class=\"num pct {_accuracy_tone(row['top1_accuracy'])}\">{row['top1_accuracy']}%</td>"
        f"<td class=\"num pct {_accuracy_tone(row['topk_accuracy'])}\">{row['topk_accuracy']}%</td></tr>"
        for row in stage.by_category
    )
    return f"""
    <section class="card">
      <p class="section-tag">5. Results by role</p>
      <h2>{escape(title)}</h2>
      <p class="lead">{escape(_experiment_lead(stage))} Figures use the match score.</p>
      <table>
        <thead>
          <tr>
            <th>IT role</th>
            <th class="num">Resumes</th>
            <th class="num">Best match</th>
            <th class="num">In the first {stage.top_k}</th>
          </tr>
        </thead>
        <tbody>{category_rows}</tbody>
      </table>
    </section>
"""


def _shown_skills(skills: list[str]) -> list[str]:
    noise = {
        "successful", "focus", "focused", "skilled", "organization",
        "install", "installing", "installed", "installation",
        "developer", "developers", "methodologies", "methodology",
        "maintenance", "maintaining", "administration", "updates",
        "interactive", "systems administrator", "system administrator",
    }
    return [skill for skill in skills if skill not in noise]


def _skill_gap_examples_section(stages: list[StageReport]) -> str:
    role_terms = {
        "html", "css", "javascript", "react", "angular", "vue",
        "java", "python", "node.js", "sql", "figma", "wireframes",
        "ux design", "ui design", "user experience", "docker",
        "kubernetes", "aws", "linux", "terraform", "cisco",
    }

    def richness(matching: list[str], gaps: list[str]) -> int:
        terms = matching + gaps
        return sum(3 if term in role_terms else 1 for term in terms)

    correct = None
    missed = None
    for stage in stages:
        for result in stage.results:
            if not result.top_jobs:
                continue
            job = result.top_jobs[0]
            matching = _shown_skills(job.matching_skills)
            gaps = _shown_skills(job.skill_gaps)
            score = richness(matching, gaps)
            if score == 0:
                continue
            chosen = (score, result, job, matching, gaps)
            if job.correct and (correct is None or score > correct[0]):
                correct = chosen
            if not job.correct and (missed is None or score > missed[0]):
                missed = chosen
    picked = [item[1:] for item in (correct, missed) if item is not None]
    if not picked:
        return ""
    blocks = []
    for result, job, matching, gaps in picked:
        note = (
            "The first-ranked job is the same IT role as the resume."
            if job.correct
            else "The first-ranked job is a different IT role. The gap list shows job skills absent from the resume."
        )
        blocks.append(
            f"""
      <div class="skill-example">
        <h4>Resume {escape(result.resume_id)} ({escape(result.resume_category)}) → rank-1: {escape(job.title)}</h4>
        <p class="caption">{escape(note)}</p>
        <p class="parts">Match score {job.score}.</p>
        {_skill_gap_boxes(matching, gaps)}
      </div>"""
        )
    return f"""
    <section class="card">
      <p class="section-tag">6. Skill-gap analysis</p>
      <h2>Skill-gap analysis</h2>
      <p class="lead">For the job ranked first by the match score, skills found on both texts are listed beside skills required by the job and absent from the resume. Pairs with no skill terms are omitted.</p>
      {"".join(blocks)}
    </section>
"""


def _ranked_evidence_section(small: StageReport) -> str:
    blocks: list[str] = []
    for item in small.results:
        rank_rows = []
        for index, job in enumerate(item.top_jobs[: small.top_k], start=1):
            pill = "same" if job.correct else "different"
            label = "Same" if job.correct else "Different"
            rank_rows.append(
                f"<tr><td>{index}</td><td>{escape(job.title)}</td><td>{escape(job.category)}</td>"
                f'<td class="num">{job.score}</td>'
                f'<td><span class="pill {pill}">{label}</span></td></tr>'
            )
        top = item.top_jobs[0]
        best_class = "yes" if item.top1_correct else "no"
        found_class = "yes" if item.topk_correct else "no"
        blocks.append(
            f"""
      <article class="evidence">
        <div class="evidence-head">
          <span class="badge">Resume {escape(item.resume_id)}</span>
          <span>Profile: {escape(item.resume_category)}</span>
          <span>Best match: <span class="{best_class}">{"Yes" if item.top1_correct else "No"}</span></span>
          <span>Found in first {small.top_k}: <span class="{found_class}">{"Yes" if item.topk_correct else "No"}</span></span>
        </div>
        <table>
          <thead>
            <tr><th>Rank</th><th>Job title</th><th>Job occupation</th><th class="num">Score</th><th>vs profile</th></tr>
          </thead>
          <tbody>{"".join(rank_rows)}</tbody>
        </table>
        <p class="parts">Rank 1 blend: {top.score}.</p>
        {_skill_gap_boxes(top.matching_skills, top.skill_gaps)}
      </article>"""
        )
    return f"""
    <section class="card">
      <p class="section-tag">Appendix</p>
      <h2>Ranked evidence (controlled sample)</h2>
      <p class="lead">Full top-{small.top_k} lists for all {len(small.results)} resumes (blend rank).</p>
      {"".join(blocks)}
    </section>
"""


def _semantic_comparison_note(small: StageReport | None, medium: StageReport | None) -> str:
    notes = []
    for label, stage in (("controlled", small), ("broader", medium)):
        if stage is None:
            continue
        match = _comparison_row(stage, "Blend")
        semantic = _comparison_row(stage, "Semantic matching")
        if not match or not semantic:
            continue
        if semantic["top1_accuracy"] == match["top1_accuracy"]:
            relation = "matched"
        elif semantic["top1_accuracy"] < match["top1_accuracy"]:
            relation = "was lower than"
        else:
            relation = "was higher than"
        notes.append(
            f"On the {label} sample, semantic best match {relation} the match score "
            f"({semantic['top1_accuracy']}% versus {match['top1_accuracy']}%)."
        )
    return " ".join(notes)


def _limitations_next_steps(stages: list[StageReport]) -> str:
    small = _stage_by_name(stages, "small")
    medium = _stage_by_name(stages, "medium")
    summary_parts: list[str] = []
    if small:
        blend = _comparison_row(small, "Blend")
        if blend:
            summary_parts.append(
                f"On the controlled sample the match score reached {blend['top1_accuracy']}% best match (MRR {blend['mrr']:.3f})."
            )
    if medium:
        blend = _comparison_row(medium, "Blend")
        if blend:
            summary_parts.append(
                f"On the broader sample it reached {blend['top1_accuracy']}% best match (MRR {blend['mrr']:.3f})."
            )
    summary = " ".join(summary_parts)
    semantic_note = _semantic_comparison_note(small, medium)
    return f"""
    <section class="card bottom">
      <p class="section-tag" style="color:#93c5fd">7. Conclusion</p>
      <h2>Conclusion</h2>
      <p>{summary} Jobs were ranked by the match score. {semantic_note}</p>
      <p style="margin-top:16px"><strong>Limitations</strong></p>
      <ul class="clean">
        <li>Each role contributes only 2 or 3 resumes, so the percentages illustrate the method rather than estimate a population rate.</li>
        <li>Role labels are assigned from phrases in the resume and the job title.</li>
      </ul>
      <p style="margin-top:16px"><strong>Remaining proposed work</strong></p>
      <ul class="clean">
        <li>The interactive application for recruiters and job seekers is not built.</li>
      </ul>
    </section>
"""


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
