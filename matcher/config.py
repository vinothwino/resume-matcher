"""Run sizes, dataset handles, and category labels used for accuracy checks."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS_CACHE = ROOT / "data" / "skills_it.txt"
REPORTS_DIR = ROOT / "reports"

FLOREX_SKILLS_IT_URL = (
    "https://raw.githubusercontent.com/florex/resume_corpus/master/skills_it.txt"
)

RESUME_DATASET = "snehaanbhawal/resume-dataset"
RESUME_FILE = "Resume/Resume.csv"
JOB_DATASET = "avinashmynampati/human-vs-fake-vs-ai-generated-job-descriptions"
JOB_FILE = "Final_Job_Postings_Dataset.csv"

RANDOM_SEED = 42
TOP_K = 3

# Blend used to rank jobs. Title stays small so a short title cannot carry the match.
# Skill coverage stays at 10%: 20% lowered best-match accuracy on the broader, mixed sample.
BODY_WEIGHT = 0.80
TITLE_WEIGHT = 0.10
SKILL_WEIGHT = 0.10

# Controlled check: few categories, one obvious job family each.
SMALL_EVAL = {
    "name": "small",
    "resumes_per_category": 2,
    "jobs_per_category": 2,
    "categories": [
       "HR",
        "SALES",
        "DESIGNER",
        "FINANCE",
        "BANKING",
        "DIGITAL-MEDIA",
        "ENGINEERING",
    ],
}

# Broader check: more occupations and a larger mixed job pool.
MEDIUM_EVAL = {
    "name": "medium",
    "resumes_per_category": 3,
    "jobs_per_category": 5,
    "categories": [
        "INFORMATION-TECHNOLOGY",
        "TEACHER",
        "ACCOUNTANT",
        "HEALTHCARE",
        "CHEF",
        "HR",
        "SALES",
        "DESIGNER",
        "FINANCE",
        "BANKING",
        "DIGITAL-MEDIA",
        "ENGINEERING",
    ],
}

# Longest matching phrase wins, so "software engineer" stays IT
# rather than falling through to a generic engineering rule.
CATEGORY_TITLE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "INFORMATION-TECHNOLOGY": (
        "software engineer",
        "software developer",
        "full stack",
        "frontend developer",
        "front end developer",
        "backend developer",
        "web developer",
        "data scientist",
        "data engineer",
        "devops",
        "systems administrator",
        "system administrator",
        "it support",
    ),
    "TEACHER": ("teacher", "instructor", "professor", "tutor"),
    "ACCOUNTANT": ("accountant", "bookkeeper", "accounts payable", "accounts receivable"),
    "HEALTHCARE": (
        "registered nurse",
        "nurse",
        "physician",
        "physical therapist",
        "medical assistant",
        "healthcare",
    ),
    "CHEF": ("executive chef", "sous chef", "chef", "line cook", "cook"),
    "HR": (
        "human resources",
        "hr manager",
        "hr generalist",
        "recruiter",
        "talent acquisition",
    ),
    "SALES": (
        "sales representative",
        "account executive",
        "sales manager",
        "inside sales",
        "business development",
    ),
    "DESIGNER": (
        "graphic designer",
        "ux designer",
        "ui designer",
        "visual designer",
        "product designer",
    ),
    "FINANCE": (
        "financial analyst",
        "finance manager",
        "financial controller",
        "investment analyst",
    ),
    "BANKING": ("loan officer", "credit analyst", "bank teller", "branch manager", "banking"),
    "DIGITAL-MEDIA": (
        "social media",
        "content writer",
        "digital marketing",
        "video editor",
        "copywriter",
    ),
    "ENGINEERING": (
        "mechanical engineer",
        "civil engineer",
        "electrical engineer",
        "design engineer",
        "project engineer",
    ),
}
