"""Services with fixtures (no network): board URL detection and parsing, HTML, intake."""

import pytest

from app.errors import BadInputError
from app.services.ats import detect, parse_ashby, parse_greenhouse, parse_lever
from app.services.html_text import html_to_text
from app.services.intake import extract
from app.services.intake.clean_text import clean
from tests.conftest import CV_TEXT, docx_bytes, make_settings, text_pdf


def test_detect_board_urls():
    gh = detect("https://job-boards.greenhouse.io/braze/jobs/8222294&utm_medium=job_board")
    assert gh and (gh.ats, gh.slug, gh.job_id) == ("greenhouse", "braze", "8222294")
    lv = detect("https://jobs.eu.lever.co/acme/1234-abcd?lever-source=x")
    assert lv and lv.ats == "lever" and lv.eu and lv.job_id == "1234-abcd"
    ab = detect("https://jobs.ashbyhq.com/Ashby/7458d4e9")
    assert ab and ab.slug == "Ashby" and ab.job_id == "7458d4e9"
    emb = detect("https://boards.greenhouse.io/embed/job_app?for=acme&token=55")
    assert emb and emb.slug == "acme" and emb.job_id == "55"
    assert detect("https://www.linkedin.com/jobs/view/1") is None


def test_parse_greenhouse_unescapes_html_and_finds_own_domain():
    data = {
        "jobs": [
            {
                "id": 1,
                "title": "Data Engineer",
                "company_name": "Acme",
                "location": {"name": "Berlin, Germany"},
                "first_published": "2026-10-10T08:00:00-04:00",
                "absolute_url": "https://careers.acme.com/job/1",
                "content": (
                    "&lt;h3&gt;What you bring&lt;/h3&gt;"
                    "&lt;ul&gt;&lt;li&gt;Python&lt;/li&gt;&lt;/ul&gt;"
                ),
            }
        ]
    }
    [j] = parse_greenhouse("acme", data)
    assert j.posted_at and j.posted_at.isoformat() == "2026-10-10"
    assert j.own_domain == "careers.acme.com"
    assert "What you bring" in j.text and "• Python" in j.text and "<" not in j.text
    assert j.url == "https://job-boards.greenhouse.io/acme/jobs/1"


def test_parse_lever_joins_lists():
    data = [
        {
            "id": "x1",
            "text": "ML Engineer",
            "createdAt": 1791566108174,
            "categories": {"location": "Berlin", "allLocations": ["Berlin", "Remote"]},
            "hostedUrl": "https://jobs.lever.co/acme/x1",
            "applyUrl": "https://jobs.lever.co/acme/x1/apply",
            "workplaceType": "hybrid",
            "country": "DE",
            "descriptionPlain": "Intro",
            "lists": [{"text": "Who you are", "content": "<li>PyTorch</li>"}],
            "additionalPlain": "",
        }
    ]
    [j] = parse_lever("acme", data)
    assert "Who you are" in j.text and "PyTorch" in j.text
    assert j.country_code == "DE" and j.workplace_type == "hybrid" and j.posted_at is not None


def test_parse_ashby():
    data = {
        "jobs": [
            {
                "title": "Backend Engineer",
                "location": "Berlin",
                "isRemote": False,
                "workplaceType": "OnSite",
                "publishedAt": "2026-10-01T10:00:00.000+00:00",
                "jobUrl": "https://jobs.ashbyhq.com/acme/u1",
                "applyUrl": "https://jobs.ashbyhq.com/acme/u1/application",
                "descriptionPlain": "Go and PostgreSQL",
                "address": {"postalAddress": {"addressCountry": "Germany"}},
            }
        ]
    }
    [j] = parse_ashby("acme", data)
    assert j.external_id == "u1" and j.workplace_type == "onsite" and "Germany" in j.location_text


def test_html_to_text_skips_scripts():
    assert html_to_text("<p>Hi</p><script>x()</script><ul><li>A</li></ul>") == "Hi\n\n• A"


def test_clean_text_strips_contacts_and_personal_lines():
    out = clean(CV_TEXT)
    assert "alex@example.com" not in out and "2345 6789" not in out
    assert "Geburtsdatum" not in out
    assert "03/2020 - present" in out and "2018 - 2020" in out  # dates survive


def test_intake_pdf_docx_text_and_rejections():
    s = make_settings()
    assert extract(s, filename="cv.pdf", data=text_pdf(CV_TEXT)).source_type == "pdf"
    docx = extract(s, filename="cv.docx", data=docx_bytes(CV_TEXT))
    assert docx.source_type == "docx" and "Apache Airflow" in docx.text
    assert extract(s, text=CV_TEXT).label == "Pasted text"
    with pytest.raises(BadInputError, match="scan"):
        extract(s, filename="scan.pdf", data=text_pdf("hi"))
    with pytest.raises(BadInputError, match=".doc"):
        extract(s, filename="old.doc", data=b"\xd0\xcf\x11\xe0")
    with pytest.raises(BadInputError, match="scan or photo"):
        extract(s, filename="me.png", data=b"\x89PNG....")
