from src.models import Job
from src.verification import verify_job


def make_job(**kwargs):
    values = dict(
        title="SOC Analyst L1", company="Example Security Pvt Ltd", location="Kochi",
        source="LinkedIn (user-submitted)",
        source_url="https://www.linkedin.com/jobs/view/123",
        link="https://www.linkedin.com/jobs/view/123",
        description="Freshers welcome. Monitor security alerts.",
        official_url="", company_website="",
    )
    values.update(kwargs)
    return Job(**values)


def test_linkedin_only_listing_is_unverified():
    assert verify_job(make_job()).verification_status == "UNVERIFIED"


def test_upfront_registration_fee_is_suspicious():
    item = verify_job(make_job(description="Pay a registration fee to secure this job."))
    assert item.verification_status == "SUSPICIOUS"
    assert item.risk_flags


def test_unrelated_domain_is_not_cross_checked():
    item = make_job(
        official_url="https://not-example.org/careers/soc-analyst-l1",
        company_website="https://example.com",
    )
    assert verify_job(item).verification_status == "UNVERIFIED"


def test_personal_email_is_a_warning_not_automatic_proof_of_fraud():
    item = verify_job(make_job(description="Contact recruiter@example@gmail.com"))
    assert item.verification_status == "UNVERIFIED"
    assert item.risk_flags


def test_no_fee_statement_does_not_trigger_false_suspicion():
    item = verify_job(make_job(description="No registration fee or security deposit is required."))
    assert item.verification_status == "UNVERIFIED"
    assert not item.risk_flags
