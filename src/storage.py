from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path

from .models import Job


class JobStore:
    def __init__(self, db_path: str = "data/jobs.db") -> None:
        self.path = Path(db_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self._initialize()

    def _initialize(self) -> None:
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY, title TEXT NOT NULL, company TEXT NOT NULL,
                location TEXT NOT NULL, source TEXT NOT NULL, source_url TEXT NOT NULL,
                link TEXT NOT NULL, posted_date TEXT NOT NULL, apply_by TEXT NOT NULL,
                experience TEXT NOT NULL, match_reason TEXT NOT NULL,
                first_seen TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, notified_at TEXT,
                description TEXT NOT NULL DEFAULT '', category TEXT NOT NULL DEFAULT 'Other',
                verification_status TEXT NOT NULL DEFAULT 'UNVERIFIED',
                verification_notes TEXT NOT NULL DEFAULT 'Not checked',
                official_url TEXT NOT NULL DEFAULT '', company_website TEXT NOT NULL DEFAULT '',
                risk_flags TEXT NOT NULL DEFAULT ''
            )"""
        )
        existing = {row[1] for row in self.connection.execute("PRAGMA table_info(jobs)")}
        migrations = {
            "description": "TEXT NOT NULL DEFAULT ''",
            "category": "TEXT NOT NULL DEFAULT 'Other'",
            "verification_status": "TEXT NOT NULL DEFAULT 'UNVERIFIED'",
            "verification_notes": "TEXT NOT NULL DEFAULT 'Not checked'",
            "official_url": "TEXT NOT NULL DEFAULT ''",
            "company_website": "TEXT NOT NULL DEFAULT ''",
            "risk_flags": "TEXT NOT NULL DEFAULT ''",
        }
        for column, definition in migrations.items():
            if column not in existing:
                self.connection.execute(f"ALTER TABLE jobs ADD COLUMN {column} {definition}")
        self.connection.commit()

    @staticmethod
    def _job_id(job: Job) -> str:
        identity = "|".join([job.title.lower(), job.company.lower(), job.link.lower().split("#", 1)[0]])
        return hashlib.sha256(identity.encode("utf-8")).hexdigest()

    def add_jobs(self, jobs: list[Job]) -> int:
        inserted = 0
        for job in jobs:
            cursor = self.connection.execute(
                """INSERT OR IGNORE INTO jobs
                (id,title,company,location,source,source_url,link,posted_date,apply_by,
                 experience,match_reason,description,category,verification_status,
                 verification_notes,official_url,company_website,risk_flags)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    self._job_id(job), job.title, job.company, job.location, job.source,
                    job.source_url, job.link, job.posted_date, job.apply_by, job.experience,
                    job.match_reason, job.description, job.category, job.verification_status,
                    job.verification_notes, job.official_url, job.company_website, "; ".join(job.risk_flags),
                ),
            )
            inserted += cursor.rowcount
        self.connection.commit()
        return inserted

    def pending_jobs(self) -> list[dict]:
        rows = self.connection.execute(
            "SELECT * FROM jobs WHERE notified_at IS NULL ORDER BY first_seen DESC"
        ).fetchall()
        return [dict(row) for row in rows]

    def mark_notified(self, job_ids: list[str]) -> None:
        if not job_ids:
            return
        self.connection.executemany(
            "UPDATE jobs SET notified_at=CURRENT_TIMESTAMP WHERE id=?",
            [(job_id,) for job_id in job_ids],
        )
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()
