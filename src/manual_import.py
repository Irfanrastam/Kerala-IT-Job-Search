"""Import LinkedIn jobs that the user chooses to add manually via CSV."""
from __future__ import annotations

import csv
from pathlib import Path
from urllib.parse import urlparse

from .models import Job

REQUIRED_COLUMNS = {"title", "company", "location", "job_url"}


def import_linkedin_csv(path: str | Path) -> tuple[list[Job], list[str]]:
    csv_path = Path(path)
    if not csv_path.exists():
        return [], []

    jobs: list[Job] = []
    warnings: list[str] = []
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        columns = set(reader.fieldnames or [])
        missing = REQUIRED_COLUMNS - columns
        if missing:
            return [], [f"LinkedIn import skipped: missing CSV columns: {', '.join(sorted(missing))}"]

        for line_number, row in enumerate(reader, start=2):
            title = (row.get("title") or "").strip()
            company = (row.get("company") or "").strip()
            location = (row.get("location") or "").strip()
            job_url = (row.get("job_url") or "").strip()
            parsed = urlparse(job_url)
            if not title or not company or not location or parsed.scheme not in {"http", "https"} or not parsed.netloc:
                warnings.append(f"LinkedIn import line {line_number}: skipped incomplete row or invalid job URL.")
                continue
            host = (parsed.hostname or "").lower()
            if host != "linkedin.com" and not host.endswith(".linkedin.com"):
                warnings.append(f"LinkedIn import line {line_number}: URL is not a LinkedIn URL; retained only if you intended a different source.")

            jobs.append(
                Job(
                    title=title,
                    company=company,
                    location=location,
                    source="LinkedIn (user-submitted)",
                    source_url=job_url,
                    link=job_url,
                    posted_date=(row.get("posted_date") or "Not listed").strip(),
                    apply_by=(row.get("apply_by") or "Not listed").strip(),
                    description=(row.get("description") or "").strip(),
                    experience=(row.get("experience") or "Not specified").strip(),
                    official_url=(row.get("official_url") or "").strip(),
                    company_website=(row.get("company_website") or "").strip(),
                )
            )
    return jobs, warnings
