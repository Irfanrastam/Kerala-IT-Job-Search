from __future__ import annotations

import re
from datetime import date, datetime

from .models import Job

QA_PATTERNS = [
    r"\bqa\b",
    r"quality assurance",
    r"quality analyst",
    r"software test(?:er|ing)?",
    r"manual test(?:er|ing)?",
    r"automation test(?:er|ing)?",
    r"test engineer",
    r"testing trainee",
    r"testing intern",
    r"functional test(?:er|ing)?",
    r"api test(?:er|ing)?",
    r"performance test(?:er|ing)?",
    r"\btest analyst\b",
    r"\btest associate\b",
    r"\buat test(?:er|ing)?\b",
    r"support.{0,20}testing",
]

CYBER_PATTERNS = [
    r"\bsoc\b",
    r"security operations",
    r"cyber ?security",
    r"information security",
    r"\binfosec\b",
    r"security analyst",
    r"security engineer",
    r"security operations analyst",
    r"incident response",
    r"threat (?:monitoring|intelligence|analyst)",
    r"vulnerability (?:assessment|management|analyst)",
    r"penetration test(?:er|ing)?",
    r"\bvapt\b",
    r"application security",
    r"appsec",
    r"cloud security",
    r"network security",
    r"security trainee",
    r"security intern",
    r"cyber ?security intern",
    r"information security intern",
    r"grc analyst",
    r"security compliance",
]

SENIOR_PATTERNS = [
    r"\bsenior\b",
    r"\blead\b",
    r"\bprincipal\b",
    r"\bmanager\b",
    r"\barchitect\b",
    r"\bhead of\b",
    r"\bteam lead\b",
    r"\bdirector\b",
]

EXPERIENCE_PATTERNS = [
    re.compile(r"(?P<min>\d+(?:\.\d+)?)\s*(?:-|–|—|to)\s*(?P<max>\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)", re.I),
    re.compile(r"(?P<min>\d+(?:\.\d+)?)\s*\+\s*(?:years?|yrs?)", re.I),
    re.compile(r"(?P<min>\d+(?:\.\d+)?)\s*(?:years?|yrs?)\s+(?:of\s+)?experience", re.I),
]
MONTH_EXPERIENCE_PATTERNS = [
    re.compile(r"(?P<min>\d+(?:\.\d+)?)\s*(?:-|–|—|to)\s*(?P<max>\d+(?:\.\d+)?)\s*months?", re.I),
    re.compile(r"(?P<min>\d+(?:\.\d+)?)\s*months?\s+(?:of\s+)?experience", re.I),
]


def parse_date(value: str) -> date | None:
    value = re.sub(r"[,|]", " ", value or "")
    value = re.sub(r"\s+", " ", value).strip()
    for fmt in ("%d %b %Y", "%d %B %Y", "%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            pass
    return None


def classify_job(job: Job) -> str:
    text = job.searchable_text
    matches_qa = any(re.search(pattern, text, re.I) for pattern in QA_PATTERNS)
    matches_cyber = any(re.search(pattern, text, re.I) for pattern in CYBER_PATTERNS)
    if matches_qa and matches_cyber:
        return "QA + Cybersecurity"
    if matches_cyber:
        return "Cybersecurity"
    if matches_qa:
        return "QA / Software Testing"
    return "Other"


def experience_label(text: str) -> tuple[str, bool]:
    lower = text.lower()
    if re.search(r"\b(fresher|freshers|entry[- ]level|no experience|0\s*(?:-|to)\s*1\s*years?)\b", lower):
        return "Fresher / 0–1 year", True

    for pattern in EXPERIENCE_PATTERNS:
        match = pattern.search(lower)
        if not match:
            continue
        minimum = float(match.group("min"))
        maximum = float(match.groupdict().get("max") or minimum)
        if maximum <= 1:
            return "Up to 1 year", True
        return f"{minimum:g}–{maximum:g} years (above fresher target)", False

    # LinkedIn-imported rows may provide a concise value such as "3 years"
    # without the phrase "of experience". Treat that field as an explicit requirement.
    concise_years = re.search(r"\b(?P<min>\d+(?:\.\d+)?)\s*(?:years?|yrs?)\b", lower)
    if concise_years:
        minimum = float(concise_years.group("min"))
        if minimum <= 1:
            return "Up to 1 year", True
        return f"{minimum:g}+ years (above fresher target)", False

    for pattern in MONTH_EXPERIENCE_PATTERNS:
        match = pattern.search(lower)
        if not match:
            continue
        minimum = float(match.group("min"))
        maximum = float(match.groupdict().get("max") or minimum)
        if maximum <= 12:
            return "Fresher / 0–1 year", True
        return f"{minimum:g}–{maximum:g} months (above fresher target)", False

    concise_months = re.search(r"\b(?P<min>\d+(?:\.\d+)?)\s*months?\b", lower)
    if concise_months:
        minimum = float(concise_months.group("min"))
        if minimum <= 12:
            return "Fresher / 0–1 year", True
        return f"{minimum:g}+ months (above fresher target)", False

    if re.search(r"\b(2|3|4|5|6|7|8|9|10)\s*\+\s*(?:years?|yrs?)\b", lower):
        return "2+ years (above fresher target)", False
    if re.search(r"\b(intern|internship|trainee|apprentice)\b", lower):
        return "Internship / trainee (experience not specified)", True
    return "Not specified", True


def is_relevant(job: Job) -> bool:
    title = job.title.lower()
    text = f"{job.title} {job.description} {job.experience}".lower()
    # Evaluate seniority from the job title only: role descriptions commonly
    # refer to senior colleagues even when the vacancy itself is junior.
    if any(re.search(pattern, title) for pattern in SENIOR_PATTERNS):
        return False

    category = classify_job(job)
    if category == "Other":
        return False

    experience, suitable = experience_label(text)
    if not suitable:
        return False

    closing_date = parse_date(job.apply_by)
    if closing_date and closing_date < date.today():
        return False

    job.experience = experience
    job.category = category
    matched: list[str] = []
    if any(re.search(pattern, text) for pattern in QA_PATTERNS):
        matched.append("QA / software testing")
    if any(re.search(pattern, text) for pattern in CYBER_PATTERNS):
        matched.append("Cybersecurity")
    job.match_reason = ", ".join(matched)
    return True


def filter_jobs(jobs: list[Job]) -> list[Job]:
    filtered: list[Job] = []
    seen: set[tuple[str, str, str]] = set()
    for job in jobs:
        if not is_relevant(job):
            continue
        identity = (job.title.lower(), job.company.lower(), job.link.lower())
        if identity in seen:
            continue
        seen.add(identity)
        filtered.append(job)
    return filtered
