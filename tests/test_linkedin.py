import csv

from src.linkedin import build_linkedin_search_url, get_linkedin_searches
from src.manual_import import import_linkedin_csv


def test_linkedin_search_url_includes_keywords_and_entry_level_filter():
    url = build_linkedin_search_url("SOC Analyst")
    assert url.startswith("https://www.linkedin.com/jobs/search/?")
    assert "SOC+Analyst" in url or "SOC%20Analyst" in url
    assert "f_E=1%2C2" in url


def test_linkedin_search_links_cover_cybersecurity_internships():
    terms = {item["keyword"] for item in get_linkedin_searches()}
    assert "SOC Analyst" in terms
    assert "Cybersecurity Intern" in terms
    assert "Information Security Intern" in terms


def test_import_manual_linkedin_csv(tmp_path):
    path = tmp_path / "linkedin_jobs.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "title", "company", "location", "job_url", "description", "experience",
            "posted_date", "apply_by", "official_url", "company_website",
        ])
        writer.writeheader()
        writer.writerow({
            "title": "SOC Analyst L1", "company": "Example Security",
            "location": "Kochi", "job_url": "https://www.linkedin.com/jobs/view/12345",
            "description": "Freshers welcome", "experience": "Fresher",
        })
    jobs, warnings = import_linkedin_csv(path)
    assert warnings == []
    assert len(jobs) == 1
    assert jobs[0].source == "LinkedIn (user-submitted)"
    assert jobs[0].title == "SOC Analyst L1"
