"""Orchestrator wiring with fake agents: no network, no keys."""

from app.agents import orchestrator
from app.agents.search_agent import RawPosting
from app.agents.verify_agent import VerifiedPosting
from app.models.schemas import Posting, Preferences, Profile, RejectedPosting, VerifiedFlags
from tests.conftest import make_settings

FLAGS = VerifiedFlags(company_exists=True, posting_live=True, recent=True)


class FakeClient:
    model = "fake-model"

    def __init__(self, settings):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return None


def raw(i: int, loc: str) -> RawPosting:
    return RawPosting(f"Role {i}", "Acme", f"https://x.io/{loc}/{i}", "", None, "x.io")


async def test_widens_location_until_enough_postings(monkeypatch):
    locations: list[str] = []

    async def fake_search(profile, prefs, tavily, limit=20, exclude=None):
        locations.append(prefs.location)
        return [raw(i, prefs.location) for i in range(3)]

    async def fake_verify(postings, tavily):
        kept = [VerifiedPosting(raw=p, flags=FLAGS, notes=[]) for p in postings[:2]]
        dropped = [RejectedPosting(title=p.title, url=p.url, reason="dead") for p in postings[2:]]
        return kept, dropped

    async def fake_score(postings, profile, prefs, llm, tavily):
        return [
            Posting(title=vp.raw.title, company="Acme", url=vp.raw.url, verified=FLAGS, score=i % 5)
            for i, vp in enumerate(postings)
        ]

    monkeypatch.setattr(orchestrator, "LLMClient", FakeClient)
    monkeypatch.setattr(orchestrator, "TavilyService", FakeClient)
    monkeypatch.setattr(orchestrator, "search_postings", fake_search)
    monkeypatch.setattr(orchestrator, "verify_postings", fake_verify)
    monkeypatch.setattr(orchestrator, "score_postings", fake_score)

    resp = await orchestrator.run_job_search(
        Profile(target_roles=["Data Engineer"]),
        Preferences(location="Berlin"),
        make_settings(mock_mode=False),
    )
    # 2 verified per round: Berlin (2) -> Germany (4) -> World (6 >= MIN_POSTINGS)
    assert locations == ["Berlin", "Germany", "World"]
    assert len(resp.postings) == 6
    assert len(resp.rejected) == 3
    assert resp.postings == sorted(resp.postings, key=lambda p: p.score, reverse=True)
    assert any("widening" in s.message for s in resp.trace)
