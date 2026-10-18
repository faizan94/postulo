from datetime import UTC, datetime, timedelta

from app.agents.score_agent import fallback_score, to_posting
from app.agents.search_agent import (
    RawPosting,
    build_queries,
    company_from_url,
    looks_like_posting,
    title_from_result,
)
from app.agents.verify_agent import VerifiedPosting, is_recent
from app.models.schemas import Preferences, Profile, Skill, VerifiedFlags


def test_company_from_url():
    assert company_from_url("https://boards.greenhouse.io/acme-labs/jobs/123") == "Acme Labs"
    assert company_from_url("https://jobs.lever.co/foobar/abc-def") == "Foobar"
    assert company_from_url("https://zalando.jobs.personio.de/job/42") == "Zalando"
    assert company_from_url("https://join.com/companies/kiez/123-data") == "Kiez"
    assert company_from_url("https://example.com/whatever") is None


def test_title_from_result():
    assert title_from_result("Job Application for Data Engineer at Acme", None) == "Data Engineer"
    assert title_from_result("Data Engineer - Acme | Lever", "Acme") == "Data Engineer"


def test_looks_like_posting():
    assert looks_like_posting("https://boards.greenhouse.io/acme/jobs/123")
    assert not looks_like_posting("https://boards.greenhouse.io/acme")


def test_build_queries():
    profile = Profile(target_roles=["Data Engineer"], skills=["Python", "SQL"])
    queries = build_queries(profile, Preferences(location="Berlin", prompt="fintech"))
    assert queries and all("Berlin" in q for q in queries)
    assert len(queries) <= 3


def test_is_recent():
    now = datetime.now(UTC)
    assert is_recent((now - timedelta(days=3)).isoformat(), now)[0] is True
    assert is_recent((now - timedelta(days=90)).isoformat(), now)[0] is False
    assert is_recent("Mon, 13 Oct 2025 10:00:00 GMT", now)[0] is False
    assert is_recent(None, now)[0] is True


def test_score_helpers():
    skills = [Skill(name="a", status="gold"), Skill(name="b", status="red")]
    assert fallback_score(skills) == 2.5
    vp = VerifiedPosting(
        raw=RawPosting("Data Eng", "Acme", "https://x.io/a/1", "", None, "x.io"),
        flags=VerifiedFlags(company_exists=True, posting_live=True, recent=True),
        notes=[],
    )
    p = to_posting(vp, {"skills": [{"name": "Python", "status": "gold"}], "score": 7.3})
    assert p.score == 5.0 and p.company == "Acme" and p.skills[0].status == "gold"
