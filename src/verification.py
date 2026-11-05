"""Conservative job-posting checks.

These checks identify evidence and warning signs; they cannot prove a recruiter
or offer is genuine. Strong verification requires a matching vacancy on the
employer's independently confirmed official careers domain.
"""
from __future__ import annotations

import ipaddress
import re
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from .models import Job

USER_AGENT = "Mozilla/5.0 (compatible; KeralaJobHunter/1.1)"
TIMEOUT = 12

CRITICAL_RED_FLAGS = {
    "Requests an upfront registration/application/interview/processing fee": re.compile(
        r"\b(registration|application|processing|interview|job|placement)\s+(?:fee|charge)\b|\bpay\s+(?:to\s+)?(?:apply|secure|get)\s+(?:the\s+)?job\b|\brefundable\s+(?:security\s+)?deposit\b",
        re.I,
    ),
    "Requests a security deposit or payment for a job offer": re.compile(
        r"\bsecurity\s+deposit\b|\bpay\s+to\s+get\s+(?:the\s+)?job\b|\bjob\s+guarantee\s+fee\b",
        re.I,
    ),
    "Requests passwords, OTPs, or banking/card credentials": re.compile(
        r"\b(?:share|send|provide|tell\s+us)\b.{0,35}\b(password|otp|one[- ]time password|cvv|card pin|upi pin)\b|\b(?:bank login|net banking password|upi pin)\b",
        re.I,
    ),
}
WARNING_RED_FLAGS = {
    "Uses a generic personal email address; independently confirm the recruiter": re.compile(
        r"\b(?:gmail\.com|yahoo\.com|outlook\.com|hotmail\.com)\b", re.I
    ),
    "Pressures applicants to move immediately to WhatsApp/Telegram or an external chat": re.compile(
        r"\b(?:contact|message|send your cv)\b.{0,50}\b(?:whatsapp|telegram)\b|\b(?:whatsapp|telegram)\s+only\b",
        re.I,
    ),
    "Requests sensitive identity or financial information unusually early": re.compile(
        r"\b(?:send|share|upload)\b.{0,50}\b(?:aadhaar|pan card|passport|bank account|credit card)\b",
        re.I,
    ),
}
STOPWORDS = {"and", "the", "for", "of", "a", "an", "junior", "entry", "level", "intern", "internship", "trainee"}


def _host(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower().removeprefix("www.")
    except ValueError:
        return ""


def _same_site(url: str, website: str) -> bool:
    host, expected = _host(url), _host(website)
    return bool(host and expected and (host == expected or host.endswith("." + expected)))


def _title_matches_page(title: str, page_text: str) -> bool:
    page = re.sub(r"\s+", " ", page_text).casefold()
    normalized = re.sub(r"\s+", " ", title).casefold()
    if normalized and normalized in page:
        return True
    tokens = [t for t in re.findall(r"[a-z0-9]+", title.casefold()) if t not in STOPWORDS]
    return bool(tokens) and sum(t in page for t in tokens) / len(tokens) >= 0.8


def _safe_https_url(url: str) -> bool:
    """Reject non-HTTPS, local and literal private-network targets before fetching."""
    try:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        if parsed.scheme != "https" or not host or host in {"localhost", "metadata.google.internal"}:
            return False
        if host.endswith((".local", ".internal", ".localhost")):
            return False
        try:
            address = ipaddress.ip_address(host)
            if not address.is_global:
                return False
        except ValueError:
            pass
        return True
    except ValueError:
        return False


def _read_page(url: str) -> tuple[int, str, str]:
    if not _safe_https_url(url):
        raise requests.RequestException("HTTPS public URLs only")
    response = requests.get(
        url, timeout=TIMEOUT,
        headers={"User-Agent": USER_AGENT, "Accept-Language": "en-US,en;q=0.9"},
        allow_redirects=True,
    )
    response.raise_for_status()
    final_url = getattr(response, "url", url)
    if not _safe_https_url(final_url) or not _same_site(final_url, url):
        raise requests.RequestException("Verification page redirected outside its original website")
    soup = BeautifulSoup(response.text, "html.parser")
    body = soup.find("main") or soup.find("article") or soup.body or soup
    return response.status_code, body.get_text(" ", strip=True), final_url


def _has_unnegated_match(pattern: re.Pattern[str], text: str) -> bool:
    for match in pattern.finditer(text):
        nearby = text[max(0, match.start() - 65): min(len(text), match.end() + 30)].lower()
        if re.search(r"\b(?:no|not|never|without|don't|do not)\b.{0,65}\b(?:fee|fees|charge|charges|deposit|payment|pay)\b", nearby):
            continue
        return True
    return False


def verify_job(job: Job) -> Job:
    """Set verification status and risk flags for one candidate listing."""
    evidence = " ".join([job.title, job.description])
    job.risk_flags = []
    critical = [label for label, pattern in CRITICAL_RED_FLAGS.items() if _has_unnegated_match(pattern, evidence)]
    warnings = [label for label, pattern in WARNING_RED_FLAGS.items() if _has_unnegated_match(pattern, evidence)]
    job.risk_flags.extend(critical + warnings)

    if critical:
        job.verification_status = "SUSPICIOUS"
        job.verification_notes = (
            "High-risk wording detected. Do not pay or share credentials; independently contact "
            "the employer through its known official website."
        )
        return job

    if job.official_url and job.company_website:
        if not _same_site(job.official_url, job.company_website):
            job.verification_status = "UNVERIFIED"
            job.verification_notes = "The supplied vacancy URL does not share the supplied company website's domain."
            return job
        try:
            _, page_text, final_url = _read_page(job.official_url)
            company_words = [
                w for w in re.findall(r"[a-z0-9]+", job.company.casefold())
                if w not in {"pvt", "private", "limited", "ltd", "technologies", "technology", "solutions", "inc"}
            ]
            company_match = not company_words or any(word in page_text.casefold() for word in company_words)
            if _same_site(final_url, job.company_website) and _title_matches_page(job.title, page_text) and company_match:
                job.verification_status = "CROSS-CHECKED"
                job.verification_notes = (
                    "The submitted role title was found on the supplied employer-domain vacancy page. "
                    "Independently confirm the domain before applying."
                )
            else:
                job.verification_status = "UNVERIFIED"
                job.verification_notes = "The supplied employer page loaded, but the role/company could not be matched confidently."
        except requests.RequestException as exc:
            job.verification_status = "UNVERIFIED"
            job.verification_notes = f"Could not check the supplied employer page ({type(exc).__name__}). Verify it manually."
    else:
        source_host, link_host = _host(job.source_url), _host(job.link)
        is_park_board = source_host in {"infopark.in", "technopark.in"}
        if job.source.startswith("LinkedIn"):
            job.verification_status = "UNVERIFIED"
            job.verification_notes = "LinkedIn listing supplied for review; no employer careers-page match was provided."
        elif is_park_board:
            job.verification_status = "UNVERIFIED"
            job.verification_notes = (
                "Listed on an official park job board, but this is not independent confirmation by the employer."
            )
        elif source_host and link_host and (link_host == source_host or link_host.endswith("." + source_host)) and job.link != job.source_url:
            try:
                _, page_text, final_url = _read_page(job.link)
                if _same_site(final_url, job.source_url) and _title_matches_page(job.title, page_text):
                    job.verification_status = "VERIFIED"
                    job.verification_notes = (
                        "Role title found on the configured employer-domain career page. "
                        "This checks the listing, not the identity of anyone contacting you."
                    )
                else:
                    job.verification_status = "UNVERIFIED"
                    job.verification_notes = "Employer page loaded, but the job title could not be matched confidently."
            except requests.RequestException as exc:
                job.verification_status = "UNVERIFIED"
                job.verification_notes = f"Could not verify the employer job page ({type(exc).__name__})."
        else:
            job.verification_status = "UNVERIFIED"
            job.verification_notes = "No independent employer careers-page confirmation is available."

    if warnings:
        job.verification_notes += " Warning signs: " + "; ".join(warnings)
    return job
