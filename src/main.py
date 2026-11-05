from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

from .filters import filter_jobs
from .linkedin import get_linkedin_searches
from .manual_import import import_linkedin_csv
from .scrapers import scrape_all
from .storage import JobStore
from .telegram_bot import send_text
from .verification import verify_job

ROOT = Path(__file__).resolve().parents[1]
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
LOGGER = logging.getLogger("kerala_job_hunter")


def format_digest(jobs: list[dict]) -> str:
    lines = [f"KERALA QA + CYBERSECURITY JOB ALERTS — {len(jobs)} new match(es)", ""]
    for index, job in enumerate(jobs, start=1):
        category = job.get("category") or "Not classified"
        verification = job.get("verification_status") or "UNVERIFIED"
        lines.extend(
            [
                f"{index}. [{category}] {job['title']}",
                f"Company: {job['company']}",
                f"Location: {job['location']}",
                f"Experience: {job['experience']}",
                f"Posted: {job['posted_date']} | Apply by: {job['apply_by']}",
                f"Verification: {verification}",
                f"Verification notes: {job.get('verification_notes', 'Not checked')}",
                f"Risk flags: {job.get('risk_flags') or 'None detected by the basic text checker'}",
                f"Match: {job['match_reason']}",
                f"Job link: {job['link']}",
            ]
        )
        if job.get("official_url"):
            lines.append(f"Employer job page supplied: {job['official_url']}")
        lines.extend([f"Source: {job['source_url']}", ""])

    lines.extend(
        [
            "LINKEDIN ENTRY-LEVEL SEARCHES (Kerala)",
            "Open a search, review the role, then turn ON LinkedIn's Job alert toggle:",
        ]
    )
    for item in get_linkedin_searches():
        lines.append(f"• {item['keyword']}: {item['url']}")

    lines.extend(
        [
            "",
            "Important: VERIFIED/CROSS-CHECKED means a job-page match was found, not that a recruiter or offer is guaranteed genuine.",
            "Never pay registration/interview/security fees or share OTPs, passwords, UPI PINs or bank credentials.",
            "Check the employer's official website before applying.",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    load_dotenv(ROOT / ".env")
    sources_path = ROOT / "config" / "sources.json"
    sources = json.loads(sources_path.read_text(encoding="utf-8"))
    scraped, warnings = scrape_all(sources)

    linkedin_csv = ROOT / "data" / "linkedin_jobs.csv"
    linkedin_jobs, import_warnings = import_linkedin_csv(linkedin_csv)
    scraped.extend(linkedin_jobs)
    warnings.extend(import_warnings)

    matches = filter_jobs(scraped)
    for job in matches:
        verify_job(job)

    LOGGER.info(
        "Collected %d listings; %d matched fresher QA/cybersecurity filters.",
        len(scraped), len(matches),
    )
    for warning in warnings:
        LOGGER.warning(warning)

    store = JobStore(str(ROOT / "data" / "jobs.db"))
    try:
        inserted = store.add_jobs(matches)
        pending = store.pending_jobs()
        LOGGER.info("Added %d new matching job(s); %d pending notification(s).", inserted, len(pending))

        token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
        if not token or not chat_id:
            LOGGER.warning(
                "Telegram is not configured. Jobs are saved as pending. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID."
            )
            if os.getenv("VERBOSE") == "1":
                for job in pending:
                    LOGGER.info(
                        "PENDING: [%s][%s] %s | %s | %s",
                        job.get("category"), job.get("verification_status"),
                        job["title"], job["company"], job["link"],
                    )
            return 0

        if pending:
            send_text(token, chat_id, format_digest(pending))
            store.mark_notified([job["id"] for job in pending])
            LOGGER.info("Telegram alert delivered for %d job(s).", len(pending))
        else:
            LOGGER.info("No new matching vacancies. No Telegram message sent.")
    finally:
        store.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
