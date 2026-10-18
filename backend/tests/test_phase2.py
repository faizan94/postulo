"""Phase 2 (PHASE2_PLAN.md): PDF reading, role families, places, open search, API additions."""

from app.agents.intent import parse_rules
from app.domain.places import JobLocation, places
from app.domain.titles import family, match_kind
from app.schemas.common import Place
from app.services.intake.pdf import pick_best, split_columns
from tests.conftest import CV_TEXT, confirmed_cv, login, wait_done

BERLIN = Place(kind="city", name="Berlin", country_code="DE")


def test_pick_best_prefers_clean_lines_over_word_per_line():
    words = "Senior Data Engineer at Nordwind building pipelines with Python and SQL"
    broken = "\n".join(words.split())  # what pypdf's default mode returned for the team CV
    clean = words
    text, method, q = pick_best([("plain", broken), ("layout", clean)])
    assert method == "layout" and q > 90 and text == clean


def test_split_columns_reads_left_then_right():
    rows = [f"{'Left item ' + str(i):<30}{'Right item ' + str(i)}" for i in range(8)]
    out = split_columns("\n".join(rows))
    lines = [ln.strip() for ln in out.splitlines() if ln.strip()]
    assert lines[:8] == [f"Left item {i}" for i in range(8)]
    assert lines[8:] == [f"Right item {i}" for i in range(8)]


def test_role_families_match_related_titles():
    rel = family(["AI Engineer"])
    assert {"Machine Learning Engineer", "LLM Engineer", "Prompt Engineer"} <= set(rel)
    assert match_kind("Senior AI Engineer (m/w/d)", ["AI Engineer"], rel) == "exact"
    assert match_kind("Machine Learning Engineer", ["AI Engineer"], rel) == "related"
    assert match_kind("Prompt Engineer - GenAI", ["AI Engineer"], rel) == "related"
    assert match_kind("Product Designer", ["AI Engineer"], rel) is None
    assert "Machine Learning Engineer" in family(["Senior AI Engineer"])  # base title found


def test_places_regions_custom_remote_and_anywhere():
    p = places()
    europe = Place(kind="region", name="Europe")
    assert p.matches(JobLocation("Amsterdam, Netherlands"), europe)
    assert p.matches(JobLocation("Remote - EMEA", remote=True), europe)
    assert not p.matches(JobLocation("New York, NY"), europe)
    # a remote job in Germany counts for a Berlin search (D22)
    assert p.matches(JobLocation("Remote - Germany", remote=True), BERLIN)
    assert not p.matches(JobLocation("Remote - USA", remote=True), BERLIN)
    custom = p.resolve("Bielefeld")
    assert custom.kind == "city" and custom.country_code is None
    assert p.matches(JobLocation("Bielefeld, Germany"), custom)
    assert p.resolve("dach").name == "DACH"
    assert p.matches_any(JobLocation("Tokyo"), [])  # no places = Anywhere


def test_open_search_rules():
    intent = parse_rules("AI engineer, remote or Berlin, Python and PyTorch")
    assert intent.titles == ["AI Engineer"]
    assert [x.name for x in intent.places] == ["Remote", "Berlin"]
    assert intent.keywords[:2] == ["Python", "PyTorch"]
    free = parse_rules("growth hacker in Hamburg")
    assert free.titles == ["Growth hacker"] and free.places[0].name == "Hamburg"


def test_api_parse_anywhere_search_cv_detail_and_related_flag(mock_client):
    h = login(mock_client)
    cv = confirmed_cv(mock_client, h)
    parsed = mock_client.post(
        "/api/searches/parse", headers=h, json={"text": "data engineer in Berlin with Python"}
    ).json()
    assert parsed["titles"] == ["Data Engineer"] and parsed["places"][0]["name"] == "Berlin"
    assert parsed["keywords"] == ["Python"]

    detail = mock_client.get(f"/api/cv/{cv['cv_version']['id']}", headers=h).json()
    assert detail["profile"]["skills"] and detail["cv_version"]["status"] == "confirmed"

    # no places = Anywhere: jobs in Berlin, Hamburg, Munich and remote all qualify
    sid = mock_client.post(
        "/api/searches",
        headers=h,
        json={
            "cv_version_id": cv["cv_version"]["id"],
            "titles": ["Data Engineer"],
            "places": [],
            "keywords": ["Python"],
        },
    ).json()["search_id"]
    res = wait_done(mock_client, sid, h)
    assert res["status"] == "done" and res["keywords"] == ["Python"]
    places_seen = {c["place"]["name"] for c in res["results"] if c["place"]}
    assert len(places_seen) >= 2
    assert "Data Platform Engineer" in res["related_titles"]
    assert any(c["related_role"] for c in res["results"])  # role family match is flagged
    assert any(not c["related_role"] for c in res["results"])


def test_cv_text_survives_new_pdf_reader():
    import asyncio

    from app.services.intake import extract
    from tests.conftest import make_settings, text_pdf

    r = asyncio.run(extract(make_settings(), filename="cv.pdf", data=text_pdf(CV_TEXT)))
    assert r.method in ("pypdf-layout", "pdfium", "pypdf-plain")
    assert "Apache Airflow" in r.text and not r.ocr_used


def test_remote_jobs_must_be_open_to_the_users_country():
    from app.domain.remote import remote_ok_for

    def ok(text: str) -> bool:
        return remote_ok_for(JobLocation(text, None, True), "DE")

    assert ok("Remote") and ok("Remote - Germany") and ok("Remote - EU") and ok("Remote, EMEA")
    assert ok("Remote (worldwide)")
    assert not ok("Senior AI Engineer - US, Remote") and not ok("Remote (Anywhere in the U.S.)")
    assert not ok("Remote - United States") and not ok("Remote - Canada")
    assert remote_ok_for(JobLocation("Remote - US", None, True), None)  # unknown home: keep


def test_clean_text_strips_profile_links():
    from app.services.intake.clean_text import clean

    out = clean(
        "Berlin | linkedin.com/in/some-person-123 | https://www.xing.com/profile/Some_Person"
    )
    assert "linkedin.com/in" not in out and "xing.com/profile" not in out and "Berlin" in out
