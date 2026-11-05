from bs4 import BeautifulSoup

from src.scrapers import _discover_infopark_pages, _parse_table_rows


def test_infopark_table_parser_extracts_listing():
    html = """
    <table><thead><tr><th>Posted</th><th>Job Title</th><th>Company</th><th>Last Date</th></tr></thead>
    <tbody><tr>
      <td>04-11-2026</td><td>QA Analyst <a href='/job/qa-analyst'>Details</a></td>
      <td>Example Systems</td><td>30 Nov 2026</td>
    </tr></tbody></table>
    """
    soup = BeautifulSoup(html, "html.parser")
    jobs = _parse_table_rows(soup, source_name="Infopark test",
        source_url="https://infopark.in/companies-job", location="Infopark Kochi")
    assert len(jobs) == 1
    assert jobs[0].title.startswith("QA Analyst")
    assert jobs[0].company == "Example Systems"
    assert jobs[0].link == "https://infopark.in/job/qa-analyst"


def test_infopark_pagination_links_are_discovered():
    soup = BeautifulSoup("<a href='?page=2'>2</a><a href='?page=3'>3</a>", "html.parser")
    pages = _discover_infopark_pages("https://infopark.in/companies-job", soup)
    assert pages == [
        "https://infopark.in/companies-job?page=2",
        "https://infopark.in/companies-job?page=3",
    ]


def test_official_park_board_parser_extracts_security_role():
    html = """<table><tbody><tr>
      <td>04-11-2026</td><td>Application Security Engineer <a href='/job/appsec'>Details</a></td>
      <td>Example Security</td><td>30 Nov 2026</td>
    </tr></tbody></table>"""
    soup = BeautifulSoup(html, "html.parser")
    jobs = _parse_table_rows(soup, source_name="Infopark test",
        source_url="https://infopark.in/companies-job", location="Infopark Kochi")
    assert len(jobs) == 1
    assert jobs[0].title.startswith("Application Security")
