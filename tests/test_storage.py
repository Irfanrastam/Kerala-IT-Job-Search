from src.models import Job
from src.storage import JobStore


def test_storage_tracks_pending_then_notified(tmp_path):
    store = JobStore(str(tmp_path / "jobs.db"))
    item = Job(
        title="QA Analyst", company="Example Tech", location="Infopark, Kochi",
        source="Infopark", source_url="https://infopark.in/companies-job",
        link="https://example.com/jobs/qa-analyst",
        experience="Fresher / 0–1 year", match_reason="QA / software testing",
        category="QA / Software Testing", verification_status="UNVERIFIED",
        verification_notes="Park listing only",
    )
    try:
        assert store.add_jobs([item]) == 1
        assert store.add_jobs([item]) == 0
        pending = store.pending_jobs()
        assert len(pending) == 1
        assert pending[0]["category"] == "QA / Software Testing"
        store.mark_notified([pending[0]["id"]])
        assert store.pending_jobs() == []
    finally:
        store.close()
