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

# IT / software sample only. Families stay separate so a correct match
# means the right software role, not "any IT resume vs any IT job".
IT_ROLE_FAMILIES = (
    "Software development",
    "Systems administration",
    "IT support",
)

SMALL_EVAL = {
    "name": "small",
    "resumes_per_category": 2,
    "jobs_per_category": 2,
    "categories": list(IT_ROLE_FAMILIES),
}

MEDIUM_EVAL = {
    "name": "medium",
    "resumes_per_category": 3,
    "jobs_per_category": 5,
    "categories": list(IT_ROLE_FAMILIES),
}

# Phrases that place an IT resume or IT job title into one role family.
# Longest match wins.
IT_ROLE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "Software development": (
        "software engineer",
        "software developer",
        "web developer",
        "full stack",
        "frontend developer",
        "front end developer",
        "front-end developer",
        "backend developer",
        "back end developer",
        "java developer",
        "python developer",
        "devops",
        "programmer",
    ),
    "Systems administration": (
        "systems administrator",
        "system administrator",
        "network administrator",
        "linux administrator",
        "database administrator",
    ),
    "IT support": (
        "technical support",
        "desktop support",
        "service desk",
        "help desk",
        "it support",
    ),
}

# Titles that enter the IT pool. Role family (software, systems, support)
# is assigned later from IT_ROLE_KEYWORDS.
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
}
