from src.filters import classify_job, filter_jobs, is_relevant
from src.models import Job


def job(title: str, description: str = "", experience: str = "Not specified") -> Job:
    return Job(
        title=title, company="Example Tech", location="Kochi",
        source="Test source", source_url="https://example.com/jobs",
        link="https://example.com/job/1", description=description,
        experience=experience,
    )


def test_fresher_qa_role_is_included():
    item = job("QA Analyst", "Freshers can apply. 0-1 years experience.")
    assert is_relevant(item)
    assert item.experience == "Fresher / 0–1 year"
    assert item.category == "QA / Software Testing"


def test_senior_qa_role_is_excluded():
    assert not is_relevant(job("Senior QA Engineer", "5+ years experience"))


def test_two_year_test_role_is_excluded():
    assert not is_relevant(job("Software Tester", "Requires 2+ years of experience"))


def test_unrelated_role_is_excluded():
    assert not is_relevant(job("Frontend Developer", "React and JavaScript"))


def test_duplicate_jobs_are_removed():
    assert len(filter_jobs([job("QA Engineer"), job("QA Engineer")])) == 1


def test_fresher_soc_analyst_is_included():
    item = job("SOC Analyst L1", "Freshers welcome. Monitor SIEM alerts and triage incidents.")
    assert is_relevant(item)
    assert item.category == "Cybersecurity"
    assert item.experience == "Fresher / 0–1 year"


def test_cybersecurity_internship_is_included():
    item = job("Cybersecurity Intern", "Assist with security monitoring and vulnerability analysis.")
    assert is_relevant(item)
    assert item.category == "Cybersecurity"


def test_vapt_intern_is_included():
    assert is_relevant(job("VAPT Intern", "Internship for penetration testing and vulnerability assessment."))


def test_senior_security_analyst_is_excluded():
    assert not is_relevant(job("Senior Security Analyst", "SOC and SIEM operations."))


def test_classify_combined_role():
    item = job("QA / Application Security Tester", "API testing and security testing")
    assert classify_job(item) == "QA + Cybersecurity"
