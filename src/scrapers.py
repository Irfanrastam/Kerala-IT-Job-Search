"""HTML scrapers for official Infopark and Technopark job boards.

The sites can change their markup. Parsers therefore support standard tables and
common card/list layouts, and surface parsing failures instead of silently
reporting an empty result.
"""
from __future__ import annotations

import logging
import re
import time
from typing import Iterable
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup, Tag

from .models import Job

LOGGER = logging.getLogger(__name__)
USER_AGENT = "Mozilla/5.0 (compatible; KeralaQAJobHunter/1.0; +https://github.com/)"
REQUEST_TIMEOUT = 25


def fetch_soup(url: str) -> BeautifulSoup:
    response = requests.get(
        url,
        timeout=REQUEST_TIMEOUT,
        headers={"User-Agent": USER_AGENT, "Accept-Language": "en-US,en;q=0.9"},
    )
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip(" \t\r\n|•")


def _row_link(row: Tag, base_url: str) -> str:
    anchors = row.find_all("a", href=True)
    if not anchors:
        return base_url
    # Prefer an explicit detail/application link, otherwise the first row link.
    for anchor in anchors:
        label = clean_text(anchor.get_text(" ", strip=True)).lower()
        href = anchor.get("href", "")
        if any(word in label for word in ("detail", "view", "apply", "read more")):
            return urljoin(base_url, href)
    return urljoin(base_url, anchors[0].get("href", ""))


def _make_job(
    *, title: str, company: str, posted: str, closing: str, row: Tag,
    source_name: str, source_url: str, location: str,
) -> Job | None:
    title = clean_text(title)
    company = clean_text(company)
    if not title or title.lower() in {"job title", "title", "position"}:
        return None
    return Job(
        title=title,
        company=company or "Company not listed",
        location=location,
        source=source_name,
        source_url=source_url,
        link=_row_link(row, source_url),
        posted_date=clean_text(posted) or "Not listed",
        apply_by=clean_text(closing) or "Not listed",
    )


def _parse_table_rows(
    soup: BeautifulSoup, *, source_name: str, source_url: str, location: str
) -> list[Job]:
    jobs: list[Job] = []
    for table in soup.find_all("table"):
        for row in table.find_all("tr"):
            cells = row.find_all(["td", "th"], recursive=False)
            if len(cells) < 3 or any(cell.name == "th" for cell in cells):
                continue
            values = [clean_text(cell.get_text(" ", strip=True)) for cell in cells]
            # Infopark: posting date | title | company | closing date | details.
            if len(values) >= 4 and re.search(r"\d", values[0]):
                posted, title, company, closing = values[:4]
            else:
                # Generic Technopark/other official job-board table.
                joined = " ".join(values).lower()
                if not re.search(
                    r"\b(qa|test|testing|quality|soc|security|cybersecurity|infosec|vapt|penetration|vulnerability|appsec|incident response)\b",
                    joined, re.I,
                ):
                    continue
                links = row.find_all("a", href=True)
                title = clean_text(links[0].get_text(" ", strip=True)) if links else values[0]
                posted, company, closing = "Not listed", "Company not listed", "Not listed"
                if len(values) >= 3:
                    # The employer is usually one of the cells, not the title cell.
                    company = values[-2] if len(values) > 3 else values[1]
            job = _make_job(
                title=title, company=company, posted=posted, closing=closing,
                row=row, source_name=source_name, source_url=source_url,
                location=location,
            )
            if job:
                jobs.append(job)
    return jobs


def _parse_cards(
    soup: BeautifulSoup, *, source_name: str, source_url: str, location: str
) -> list[Job]:
    jobs: list[Job] = []
    selectors = "article, .job-listing, .job-item, .views-row, .career-item, .job-card, li"
    for card in soup.select(selectors):
        text = clean_text(card.get_text(" ", strip=True))
        if not text or not re.search(r"\b(qa|quality|test|testing|soc|security|cybersecurity|infosec|vapt|penetration|vulnerability|appsec|incident response)\b", text, re.I):
            continue
        anchors = card.find_all("a", href=True)
        if not anchors:
            continue
        title_anchor = next(
            (a for a in anchors if re.search(r"\b(qa|quality|test|testing|soc|security|cybersecurity|infosec|vapt|penetration|vulnerability|appsec|incident response)\b", clean_text(a.get_text(" ", strip=True)), re.I)),
            anchors[0],
        )
        title = clean_text(title_anchor.get_text(" ", strip=True))
        if not title or len(title) > 180:
            continue
        # Leave the company as unknown when it cannot be confidently isolated.
        company = "Company not listed"
        job = Job(
            title=title,
            company=company,
            location=location,
            source=source_name,
            source_url=source_url,
            link=urljoin(source_url, title_anchor.get("href", "")),
            description=text,
        )
        jobs.append(job)
    return jobs


def _discover_infopark_pages(first_url: str, soup: BeautifulSoup, max_pages: int = 12) -> list[str]:
    """Collect pagination URLs visible on the Infopark page."""
    root = urlparse(first_url)
    candidates: list[tuple[int, str]] = []
    for anchor in soup.find_all("a", href=True):
        href = urljoin(first_url, anchor["href"])
        parsed = urlparse(href)
        if parsed.netloc != root.netloc or parsed.path.rstrip("/") != root.path.rstrip("/"):
            continue
        label = clean_text(anchor.get_text(" ", strip=True))
        page_number = re.search(r"\d+", label)
        if page_number:
            candidates.append((int(page_number.group()), href))
    ordered: list[str] = []
    for _, url in sorted(candidates):
        if url not in ordered and url != first_url:
            ordered.append(url)
    return ordered[: max_pages - 1]


def scrape_infopark(source: dict) -> tuple[list[Job], list[str]]:
    url = source["url"]
    name = source["name"]
    location = source.get("location", "Infopark, Kerala")
    warnings: list[str] = []
    jobs: list[Job] = []
    try:
        first_soup = fetch_soup(url)
        jobs.extend(_parse_table_rows(first_soup, source_name=name, source_url=url, location=location))
        if not jobs:
            jobs.extend(_parse_cards(first_soup, source_name=name, source_url=url, location=location))
        for page_url in _discover_infopark_pages(url, first_soup):
            try:
                page_soup = fetch_soup(page_url)
                page_jobs = _parse_table_rows(page_soup, source_name=name, source_url=page_url, location=location)
                if not page_jobs:
                    page_jobs = _parse_cards(page_soup, source_name=name, source_url=page_url, location=location)
                jobs.extend(page_jobs)
                time.sleep(0.4)
            except requests.RequestException as exc:
                warnings.append(f"{name}: could not read pagination page {page_url}: {exc}")
    except requests.RequestException as exc:
        warnings.append(f"{name}: request failed: {exc}")
    if not jobs and not warnings:
        warnings.append(f"{name}: page loaded, but no job rows were recognized; the website layout may have changed.")
    return jobs, warnings


def scrape_technopark(source: dict) -> tuple[list[Job], list[str]]:
    url = source["url"]
    name = source["name"]
    location = source.get("location", "Technopark, Thiruvananthapuram")
    warnings: list[str] = []
    try:
        soup = fetch_soup(url)
        jobs = _parse_table_rows(soup, source_name=name, source_url=url, location=location)
        if not jobs:
            jobs = _parse_cards(soup, source_name=name, source_url=url, location=location)
        # Some versions of this board populate jobs with client-side JavaScript.
        # Do not claim an empty feed is proof there are no vacancies.
        if not jobs:
            warnings.append(
                f"{name}: the page returned no parseable job cards/tables. It may be JavaScript-rendered; check the official page manually."
            )
        return jobs, warnings
    except requests.RequestException as exc:
        return [], [f"{name}: request failed: {exc}"]


def scrape_generic(source: dict) -> tuple[list[Job], list[str]]:
    """Best-effort adapter for an employer's public careers page."""
    url = source["url"]
    name = source["name"]
    location = source.get("location", "Kerala / verify location")
    try:
        soup = fetch_soup(url)
        jobs = _parse_table_rows(soup, source_name=name, source_url=url, location=location)
        if not jobs:
            jobs = _parse_cards(soup, source_name=name, source_url=url, location=location)
        if not jobs:
            return [], [
                f"{name}: no parseable job cards/tables. This career site may require a custom adapter or JavaScript rendering."
            ]
        company_name = clean_text(source.get("company", ""))
        if company_name:
            for job in jobs:
                job.company = company_name
        return jobs, []
    except requests.RequestException as exc:
        return [], [f"{name}: request failed: {exc}"]


def _enrich_job_details(jobs: list[Job], warnings: list[str], max_details: int = 30) -> None:
    """Fetch short descriptions for QA and cybersecurity listings to inspect eligibility."""
    candidate_pattern = re.compile(
        r"\b(qa|quality|test|testing|uat|soc|security|cybersecurity|infosec|vapt|penetration|vulnerability|appsec|incident response)\b", re.I
    )
    visited: set[str] = set()
    fetched = 0
    for job in jobs:
        if fetched >= max_details:
            break
        if not candidate_pattern.search(job.title):
            continue
        if not job.link or job.link == job.source_url or job.link in visited:
            continue
        visited.add(job.link)
        try:
            detail_soup = fetch_soup(job.link)
            content = detail_soup.find("main") or detail_soup.find("article") or detail_soup.body or detail_soup
            detail_text = clean_text(content.get_text(" ", strip=True))
            if detail_text:
                job.description = detail_text[:7000]
            fetched += 1
            time.sleep(0.35)
        except requests.RequestException as exc:
            warnings.append(f"Could not inspect job details for {job.title!r}: {exc}")


def scrape_all(sources: Iterable[dict]) -> tuple[list[Job], list[str]]:
    all_jobs: list[Job] = []
    warnings: list[str] = []
    for source in sources:
        source_type = source.get("type")
        if source_type == "infopark":
            jobs, source_warnings = scrape_infopark(source)
        elif source_type == "technopark":
            jobs, source_warnings = scrape_technopark(source)
        elif source_type == "generic":
            jobs, source_warnings = scrape_generic(source)
        else:
            warnings.append(f"Unknown source type {source_type!r} for {source.get('name', 'unnamed source')}")
            continue
        all_jobs.extend(jobs)
        warnings.extend(source_warnings)
        time.sleep(0.6)  # Be polite to the official sites.
    _enrich_job_details(all_jobs, warnings)
    return all_jobs, warnings
