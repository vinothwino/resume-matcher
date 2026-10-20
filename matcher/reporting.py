"""Write JSON summary and a screenshot-ready project-review HTML report."""

import json
from html import escape
from pathlib import Path

from matcher.config import BODY_WEIGHT, REPORTS_DIR, SKILL_WEIGHT, TITLE_WEIGHT
from matcher.evaluation import RankedJob, ResumeResult, StageReport

PROJECT_REVIEW_HTML = "project-review.html"

_EXPERIMENT_TITLES: dict[str, str] = {
    "small": "Experiment 1 — Controlled sample",
    "medium": "Experiment 2 — Broader sample",
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
    .pill.same { color: var(--green); background: var(--green-bg); }
    .pill.different { color: var(--red); background: var(--red-bg); }
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
        return "—"
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
    if stage.stage == "small":
        return (
            f"7 occupations, 2 resumes and 2 labeled jobs per occupation. "
            f"{stage.resumes} resumes × {stage.jobs} jobs."
        )
    if stage.stage == "medium":
        return (
            f"12 occupations, 3 resumes and 5 labeled jobs per occupation. "
            f"{stage.resumes} resumes × {stage.jobs} jobs."
        )
    return f"{stage.resumes} resumes × {stage.jobs} jobs."


def _experiment_interpretation(stage: StageReport) -> str:
    baseline = _comparison_row(stage, "Baseline TF-IDF")
    blend = _comparison_row(stage, "Blend")
    skill = _comparison_row(stage, "Skill coverage only")
    if not baseline or not blend or not skill:
        return ""
    if stage.stage == "small":
        return (
            f"<strong>Interpretation:</strong> The blend improves Best Match "
            f"({blend['top1_accuracy']}% vs {baseline['top1_accuracy']}% for baseline TF-IDF) and MRR "
            f"({blend['mrr']:.3f} vs {baseline['mrr']:.3f}) on the controlled sample. "
            f"Skill coverage alone matches baseline on Best Match ({skill['top1_accuracy']}%) but adds signal "
            f"when combined at {int(SKILL_WEIGHT * 100)}% weight."
        )
    return (
        f"<strong>Interpretation:</strong> On the broader pool, the blend reaches "
        f"{blend['top1_accuracy']}% Best Match (baseline TF-IDF {baseline['top1_accuracy']}%). "
        f"Skill coverage alone is weak ({skill['top1_accuracy']}% Best Match) but still helps the combined ranker "
        f"versus text-only ablations in some cases."
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
    small = _stage_by_name(stages, "small")
    experiments = "".join(
        _experiment_section(stage)
        for stage in stages
        if stage.stage in _EXPERIMENT_TITLES
    )
    evidence = _ranked_evidence_section(small) if small else ""
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
    {_alignment_section()}
    {_method_section()}
    {_metrics_section(top_k, small)}
    {_baseline_blend_summary(stages, top_k)}
    {experiments}
    {_skill_gap_examples_section(small)}
    {evidence}
    {_limitations_next_steps(stages)}
  </div>
</body>
</html>
"""


def _overview_header() -> str:
    return """
    <header class="hero">
      <p class="section-tag">Overview</p>
      <h1>Does the highest-scoring job share the resume&rsquo;s occupation?</h1>
      <p class="subtitle">MCA Second Review — controlled evaluation of the Review&nbsp;1 resume–job matching approach.</p>
    </header>
"""


def _alignment_section() -> str:
    return """
    <section class="card">
      <p class="section-tag">Alignment with Review 1 Proposal</p>
      <h2>Alignment with Review 1 Proposal</h2>
      <ul class="clean">
        <li><strong>Original proposal:</strong> NLP-based resume–job matching using TF-IDF/cosine similarity, skill extraction, skill gap analysis, and explainable insights.</li>
        <li><strong>Current work:</strong> Implements the lexical matching pipeline (80/10/10 TF-IDF + skill coverage blend), occupation-specific skill mining with hold-out, and per-match score breakdown (body, title, skill coverage) plus Has/Lacking skill lists.</li>
        <li><strong>Planned next:</strong> Semantic embeddings (e.g. Sentence-BERT), richer skill extraction, and a simple interactive dashboard.</li>
      </ul>
    </section>
"""


def _method_section() -> str:
    return f"""
    <section class="card">
      <p class="section-tag">Method</p>
      <h2>Method</h2>
      <ul class="clean">
        <li>Resumes from <code>snehaanbhawal/resume-dataset</code> (ground-truth occupation on each resume).</li>
        <li>Human-written job postings from <code>avinashmynampati/human-vs-fake-vs-ai-generated-job-descriptions</code>; job occupation inferred from title keywords.</li>
        <li><strong>Ranking score (blend):</strong> {int(BODY_WEIGHT * 100)}% cosine TF-IDF on the job <em>description</em>, {int(TITLE_WEIGHT * 100)}% on the job <em>title</em>, and {int(SKILL_WEIGHT * 100)}% <em>skill coverage</em> (share of occupation skill terms on the job that also appear on the resume).</li>
        <li><strong>Skill terms:</strong> Mined from other resumes in the same occupation (unigrams/bigrams that are distinctive in-category). Resumes in the evaluation sample are held out so skill lists do not leak test text.</li>
        <li><strong>Evaluation proxy:</strong> Occupation match is used because no human relevance judgments are available—if the top job shares the resume&rsquo;s occupation label, the ranker aligned with an checkable career-area signal.</li>
      </ul>
    </section>
"""


def _metrics_section(top_k: int, small: StageReport | None) -> str:
    example = _worked_example_html(small)
    return f"""
    <section class="card">
      <p class="section-tag">Evaluation metrics</p>
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
    target = next((r for r in small.results if r.resume_id == "24655918"), None)
    if not target or len(target.top_jobs) < 3:
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
      <p class="caption">Rank 1 parts — Body: {rank1.body_score}; Title: {rank1.title_score}; Skill coverage: {rank1.skill_score}.</p>
      <p class="caption">Skill gap view for rank-1 job <em>{escape(rank1.title)}</em>:</p>
      {_skill_gap_boxes(rank1.matching_skills, rank1.skill_gaps)}
"""


def _baseline_blend_summary(stages: list[StageReport], top_k: int) -> str:
    rows = []
    for stage in stages:
        if stage.stage not in _EXPERIMENT_TITLES:
            continue
        label = _EXPERIMENT_TITLES[stage.stage]
        baseline = _comparison_row(stage, "Baseline TF-IDF")
        blend = _comparison_row(stage, "Blend")
        if not baseline or not blend:
            continue
        rows.append(
            f"<tr><td>{escape(label)}</td>"
            f"<td class=\"num pct {_accuracy_tone(baseline['top1_accuracy'])}\">{baseline['top1_accuracy']}%</td>"
            f"<td class=\"num pct {_accuracy_tone(blend['top1_accuracy'])}\">{blend['top1_accuracy']}%</td>"
            f"<td class=\"num pct {_accuracy_tone(baseline['topk_accuracy'])}\">{baseline['topk_accuracy']}%</td>"
            f"<td class=\"num pct {_accuracy_tone(blend['topk_accuracy'])}\">{blend['topk_accuracy']}%</td>"
            f"<td class=\"num\">{baseline['mrr']:.3f}</td>"
            f"<td class=\"num\">{blend['mrr']:.3f}</td></tr>"
        )
    if not rows:
        return ""
    return f"""
    <section class="card">
      <p class="section-tag">Results at a glance</p>
      <h2>Baseline TF-IDF vs blend (reported rank)</h2>
      <p class="lead">Same samples as Experiments 1 and 2. Blend = {int(BODY_WEIGHT * 100)}% description + {int(TITLE_WEIGHT * 100)}% title + {int(SKILL_WEIGHT * 100)}% skill coverage.</p>
      <table>
        <thead>
          <tr>
            <th>Sample</th>
            <th class="num">Baseline best match</th>
            <th class="num">Blend best match</th>
            <th class="num">Baseline top-{top_k}</th>
            <th class="num">Blend top-{top_k}</th>
            <th class="num">Baseline MRR</th>
            <th class="num">Blend MRR</th>
          </tr>
        </thead>
        <tbody>{"".join(rows)}</tbody>
      </table>
    </section>
"""


def _experiment_section(stage: StageReport) -> str:
    title = _EXPERIMENT_TITLES.get(stage.stage, stage.stage.title())
    topk_tone = _accuracy_tone(stage.topk_accuracy)
    interpretation = _experiment_interpretation(stage)
    category_rows = "\n".join(
        f"<tr><td>{escape(row['category'])}</td><td class=\"num\">{row['resumes']}</td>"
        f"<td class=\"num pct {_accuracy_tone(row['top1_accuracy'])}\">{row['top1_accuracy']}%</td>"
        f"<td class=\"num pct {_accuracy_tone(row['topk_accuracy'])}\">{row['topk_accuracy']}%</td></tr>"
        for row in stage.by_category
    )
    comparison_rows = "\n".join(
        f"<tr{' class=\"highlight\"' if row['method'] == 'Blend' else ''}>"
        f"<td>{escape(row['method'])}</td>"
        f"<td class=\"num pct {_accuracy_tone(row['top1_accuracy'])}\">{row['top1_accuracy']}%</td>"
        f"<td class=\"num pct {_accuracy_tone(row['topk_accuracy'])}\">{row['topk_accuracy']}%</td>"
        f"<td class=\"num\">{row.get('mrr', 0):.3f}</td></tr>"
        for row in stage.comparisons
    )
    return f"""
    <section class="card">
      <p class="section-tag">Results</p>
      <h2>{escape(title)}</h2>
      <p class="lead">{escape(_experiment_lead(stage))}</p>
      <div class="kpis">
        <div class="kpi"><span class="value">{stage.top1_accuracy}%</span><span class="label">Best match (blend)</span></div>
        <div class="kpi"><span class="value {'green' if topk_tone == 'good' else ''}">{stage.topk_accuracy}%</span><span class="label">Found in the first {stage.top_k}</span></div>
        <div class="kpi"><span class="value">{stage.mrr:.3f}</span><span class="label">MRR (blend)</span></div>
        <div class="kpi"><span class="value ink">{stage.resumes}</span><span class="label">Resumes</span></div>
        <div class="kpi"><span class="value ink">{stage.jobs}</span><span class="label">Jobs</span></div>
      </div>
      <table>
        <thead>
          <tr>
            <th>Ranking method</th>
            <th class="num">Best match</th>
            <th class="num">Found in the first {stage.top_k}</th>
            <th class="num">MRR</th>
          </tr>
        </thead>
        <tbody>{comparison_rows}</tbody>
      </table>
      <p class="caption">Highlighted row is the reported blend rank used for occupation tables and ranked evidence.</p>
      <p class="interpret">{interpretation}</p>
      <h3>By occupation</h3>
      <table>
        <thead>
          <tr>
            <th>Occupation</th>
            <th class="num">Resumes</th>
            <th class="num">Best match</th>
            <th class="num">Found in the first {stage.top_k}</th>
          </tr>
        </thead>
        <tbody>{category_rows}</tbody>
      </table>
    </section>
"""


def _skill_gap_examples_section(small: StageReport | None) -> str:
    if not small:
        return ""
    examples: list[tuple[str, RankedJob, ResumeResult]] = []
    for resume_id in ("47410104", "24655918"):
        result = next((r for r in small.results if r.resume_id == resume_id), None)
        if result and result.top_jobs:
            examples.append((resume_id, result.top_jobs[0], result))
    if not examples:
        return ""
    blocks = []
    for resume_id, job, result in examples:
        note = (
            "Correct occupation at rank 1 — skills align with the finance posting."
            if job.correct
            else "Wrong occupation at rank 1 — text similarity outranked the designer role; skill gaps highlight missing marketing terms."
        )
        blocks.append(
            f"""
      <div class="skill-example">
        <h4>Resume {escape(resume_id)} ({escape(result.resume_category)}) → rank-1: {escape(job.title)}</h4>
        <p class="caption">{escape(note)}</p>
        <p class="parts">Score {job.score} (Body {job.body_score}, Title {job.title_score}, Skill coverage {job.skill_score}).</p>
        {_skill_gap_boxes(job.matching_skills, job.skill_gaps)}
      </div>"""
        )
    return f"""
    <section class="card">
      <p class="section-tag">Explainability</p>
      <h2>Skill gap examples</h2>
      <p class="lead">Concrete Has/Lacking lists for rank-1 job pairs—supports the Review&nbsp;1 explainability objective.</p>
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
        <p class="parts">Rank 1 — Body: {top.body_score}; Title: {top.title_score}; Skill: {top.skill_score}.</p>
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


def _limitations_next_steps(stages: list[StageReport]) -> str:
    small = _stage_by_name(stages, "small")
    medium = _stage_by_name(stages, "medium")
    summary_parts: list[str] = []
    if small:
        blend = _comparison_row(small, "Blend")
        if blend:
            summary_parts.append(
                f"Controlled sample: blend {blend['top1_accuracy']}% Best Match, MRR {blend['mrr']:.3f}."
            )
    if medium:
        blend = _comparison_row(medium, "Blend")
        if blend:
            summary_parts.append(
                f"Broader sample: blend {blend['top1_accuracy']}% Best Match, MRR {blend['mrr']:.3f}."
            )
    summary = " ".join(summary_parts)
    return f"""
    <section class="card bottom">
      <p class="section-tag" style="color:#93c5fd">Closing</p>
      <h2>Limitations &amp; next steps</h2>
      <p><strong>Limitations</strong></p>
      <ul class="clean">
        <li>Small sample size (2–3 resumes per occupation)—metrics are illustrative, not statistically robust.</li>
        <li>Job occupation inferred from title keywords; some errors are label noise.</li>
        <li>Purely lexical matching today—no semantic embeddings in this build.</li>
      </ul>
      <p style="margin-top:16px"><strong>Next steps</strong></p>
      <ul class="clean">
        <li>Add semantic embeddings (e.g. Sentence-BERT / MiniLM) as a second ranking signal.</li>
        <li>Improve skill extraction and occupation lexicons.</li>
        <li>Build a simple interactive dashboard for upload-and-rank demos.</li>
      </ul>
      <p style="margin-top:18px"><strong>Bottom line:</strong> {summary} The blend ({int(BODY_WEIGHT * 100)}% description, {int(TITLE_WEIGHT * 100)}% title, {int(SKILL_WEIGHT * 100)}% skill coverage) delivers the reported rank and explainable skill-gap insights aligned with Review&nbsp;1.</p>
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
