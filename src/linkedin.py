"""Build safe LinkedIn job-search links; do not scrape LinkedIn pages.

LinkedIn's own help pages support member-created daily/weekly job alerts. Its
terms prohibit third-party crawlers and bots that scrape LinkedIn, so the agent
provides search shortcuts and accepts a user-curated CSV instead.
"""
from __future__ import annotations

from urllib.parse import urlencode

SEARCH_TERMS = [
    "SOC Analyst",
    "Security Analyst",
    "Cybersecurity Analyst",
    "Information Security Analyst",
    "Cybersecurity Intern",
    "Information Security Intern",
    "VAPT Intern",
    "Penetration Testing Intern",
    "Junior Security Engineer",
    "QA Analyst",
    "Software Tester",
]


def build_linkedin_search_url(keyword: str, location: str = "Kerala, India") -> str:
    query = urlencode(
        {
            "keywords": keyword,
            "location": location,
            # LinkedIn experience level: internship and entry-level.
            "f_E": "1,2",
        }
    )
    return f"https://www.linkedin.com/jobs/search/?{query}"


def get_linkedin_searches() -> list[dict[str, str]]:
    return [
        {
            "keyword": keyword,
            "location": "Kerala, India",
            "url": build_linkedin_search_url(keyword),
        }
        for keyword in SEARCH_TERMS
    ]


def main() -> None:
    print("LINKEDIN ENTRY-LEVEL JOB SEARCHES (Kerala, India)\n")
    for item in get_linkedin_searches():
        print(f"{item['keyword']}\n{item['url']}\n")
    print("Open each search in LinkedIn and switch the Job alert toggle ON.")
    print("Choose daily alerts by email and/or LinkedIn notifications.")


if __name__ == "__main__":
    main()
