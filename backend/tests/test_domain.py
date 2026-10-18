"""Pure logic: evidence, glossary, places, years, titles, rule extraction, matching, scores."""

from datetime import date

from app.domain.evidence import EvidenceChecker, snippet
from app.domain.glossary import glossary
from app.domain.matching import match
from app.domain.places import JobLocation, places
from app.domain.rules import extract_profile, extract_requirements, language_level
from app.domain.titles import title_matches
from app.domain.years import seniority, years_from_roles
from app.schemas.common import Evidence, Place
from app.schemas.posting import CompanyScore, JobCard, MatchScore, Requirement, SkillMatch
from app.schemas.profile import Profile, Role, SkillItem
from app.scoring import company_score
from app.scoring.match_score import score
from app.scoring.rank import rank_key
from app.scoring.summary import learn_next, skill_summary
from app.services.fakes import _DE_TEXT
from tests.conftest import CV_TEXT


def ev(q: str = "x") -> Evidence:
    return Evidence(quote=q)


def test_evidence_normalises_case_space_and_hyphen_breaks():
    src = "Erfahrung mit Kuber-\nnetes und  Python"
    c = EvidenceChecker(src)
    assert c.check("erfahrung mit kubernetes")
    assert c.check("UND PYTHON")
    assert not c.check("Java")
    assert not c.check("")


def test_snippet_is_a_substring():
    text = "We offer lunch. You know Python and SQL well. Bonus: Go."
    i = text.index("Python")
    s = snippet(text, i, i + 6)
    assert s in text and "Python" in s


def test_glossary_cv_means_computer_vision_only_in_skill_context():
    g = glossary()
    names = lambda line: {h.term.name for h in g.find(line)}  # noqa: E731
    assert "Computer Vision" in names("Skills: CV, deep learning, PyTorch")
    assert "Computer Vision" not in names("Please send your CV and cover letter")
    assert "Go" in names("Backend in Go and Python")
    assert "Go" not in names("Go-to-market strategy")
    assert g.canonical("k8s") == "Kubernetes"
    assert g.is_related("PostgreSQL", "MySQL")


def test_places_match_and_widen():
    p = places()
    berlin = Place(kind="city", name="Berlin", country_code="DE")
    germany = Place(kind="country", name="Germany", country_code="DE")
    remote = Place(kind="remote", name="Remote")
    assert p.matches(JobLocation("Berlin, Germany"), berlin)
    assert not p.matches(JobLocation("Munich, Germany"), berlin)
    assert p.matches(JobLocation("München"), germany)  # a German city counts for Germany
    assert p.matches(JobLocation("Somewhere", country_code="DE"), germany)
    assert p.matches(JobLocation("Remote - EU", remote=True), remote)
    assert p.widen(berlin) == germany
    assert p.widen(germany) is None
    assert [x.name for x in p.search("mun")][0] == "Munich"


def test_years_merge_overlaps_and_seniority():
    roles = [
        Role(title="A", company="", start="2018-01", end="2020-01", evidence=ev()),
        Role(title="B", company="", start="2019-01", end="2021-01", evidence=ev()),
    ]
    assert years_from_roles(roles, today=date(2026, 10, 1)) == 3.0
    assert seniority(1) == "junior" and seniority(6) == "senior" and seniority(None) is None


def test_titles():
    assert title_matches("Senior Data Engineer (m/w/d)", ["Data Engineer"])
    assert glossary().related_titles("Senior Software Engineer") == glossary().related_titles(
        "Software Engineer"
    )
    assert title_matches("Backend Developer", ["Backend Engineer"])
    assert not title_matches("Werkstudent Data Engineering", ["Data Engineer"])
    assert not title_matches("Data Engineering Manager", ["Data Engineer"])
    assert not title_matches("Product Designer", ["Data Engineer"])


def test_rule_requirements_are_grounded_and_section_aware():
    reqs = {r.name: r for r in extract_requirements(_DE_TEXT)}
    checker = EvidenceChecker(_DE_TEXT)
    assert all(checker.check(r.evidence.quote) for r in reqs.values())
    assert reqs["Python"].importance == "must"
    assert reqs["Kubernetes"].importance == "nice"
    assert reqs["Apache Airflow"].importance == "nice"  # only under "What you'll do"
    assert reqs["German"].level == "B2" and reqs["German"].importance == "must"
    assert reqs["Experience"].min_years == 3
    assert "Hybrid" not in reqs  # benefits are skipped


def test_language_levels():
    assert language_level("Fluent English") == "C1"
    assert language_level("Deutsch (Muttersprache)") == "native"
    assert language_level("German B2") == "B2"


def test_rule_profile():
    prof = extract_profile(CV_TEXT)
    names = {s.name for s in prof.skills}
    assert {"Python", "SQL", "Apache Airflow", "dbt", "AWS", "Docker", "Tableau"} <= names
    assert prof.place and prof.place.name == "Berlin"
    assert prof.target_titles[0] == "Data Engineer"
    assert prof.years_total is not None and prof.years_total >= 6  # education range skipped
    assert {lang.name: lang.level for lang in prof.languages}["German"] == "B2"


def _req(name: str, imp: str = "must", typ: str = "tech", **kw: object) -> Requirement:
    return Requirement(name=name, type=typ, importance=imp, evidence=ev(name), **kw)  # type: ignore[arg-type]


def _profile(*skills: str, years: float | None = 4, langs: dict[str, str] | None = None) -> Profile:
    from app.schemas.profile import LanguageItem

    return Profile(
        skills=[SkillItem(name=s, type="tech", evidence=ev(s)) for s in skills],
        languages=[LanguageItem(name=k, level=v, evidence=ev(k)) for k, v in (langs or {}).items()],
        years_total=years,
    )


def test_match_statuses():
    prof = _profile("Python", "PostgreSQL", langs={"German": "B1"})
    out = {
        m.requirement.name: m.status
        for m in match(
            prof,
            [
                _req("Python"),
                _req("MySQL"),
                _req("Kafka", "nice"),
                _req("Rust"),
                _req("German", typ="language", level="B2"),
                _req("Teamwork", typ="soft"),
            ],
        )
    }
    assert out == {
        "Python": "have",
        "MySQL": "related",
        "Kafka": "missing_nice",
        "Rust": "missing_must",
        "German": "missing_must",
        "Teamwork": "missing_nice",
    }


def test_match_score_golden_and_gates():
    prof = _profile("Python", "SQL", years=2)
    reqs = [
        _req("Python"),
        _req("SQL"),
        _req("Kafka", "nice"),
        _req("Experience", typ="years", min_years=6),
    ]
    ms = score(match(prof, reqs), prof)
    assert ms.value == 60  # base 6/7 = 86, capped at 60 by the years gate
    assert ms.must_met == "2/2" and ms.nice_met == "0/1"
    assert ms.gates_applied == ["6+ years required"]

    lang = score(match(prof, [_req("Python"), _req("German", typ="language")]), prof)
    assert lang.value == 50 and lang.thin  # language gate; only 2 requirements -> thin

    empty = score([], prof)
    assert empty.value is None and empty.thin
    soft_only = score(match(prof, [_req("Teamwork", typ="soft")] * 3), prof)
    assert soft_only.value == 0 and soft_only.must_met == "0/0"


def test_same_input_same_score():
    prof = _profile("Python")
    reqs = extract_requirements(_DE_TEXT)
    assert score(match(prof, reqs), prof) == score(match(prof, reqs), prof)


def test_company_score_bands():
    today = date(2026, 10, 18)
    v, band = company_score.score(
        company_score.CompanySignals(60, date(2026, 10, 15), "x.com"), today
    )
    assert (v, band) == (100, "strong")
    assert company_score.score(company_score.CompanySignals(None, None, None)) == (
        None,
        "not_enough_data",
    )
    v2, band2 = company_score.score(company_score.CompanySignals(2, date(2026, 1, 1), None), today)
    assert band2 == "weak" and v2 == 16


def test_rank_key_order():
    def card(
        pid: int, value: int | None, thin: bool = False, posted: date | None = None
    ) -> JobCard:
        return JobCard(
            posting_id=pid,
            title="t",
            company="c",
            match=MatchScore(value=value, must_met="", nice_met="", thin=thin),
            company_score=CompanyScore(band="pending"),
            posted_at=posted,
        )

    cards = [
        card(1, 90, thin=True),
        card(2, 70),
        card(3, 70, posted=date(2026, 10, 1)),
        card(4, 95),
    ]
    assert [c.posting_id for c in sorted(cards, key=rank_key)] == [4, 3, 2, 1]


def test_summary_and_learn_next():
    prof = _profile("Python")
    jobs = [
        match(prof, [_req("Python"), _req("Kafka")]),
        match(prof, [_req("Kafka"), _req("Docker", "nice"), _req("Spark")]),
    ]
    summ = {s.skill: s for s in skill_summary(jobs)}
    assert summ["Apache Kafka"].demand == 2 and summ["Apache Kafka"].user_status == "missing"
    assert summ["Python"].user_status == "have"
    top = learn_next(jobs, prof)
    assert top[0].skill == "Apache Kafka" and top[0].jobs_improved == 2 and top[0].unlocks == 2


def test_skill_match_round_trip():
    m = SkillMatch(requirement=_req("Python"), status="have", cv_evidence=ev("Python"))
    assert SkillMatch.model_validate(m.model_dump(mode="json")) == m


def test_llm_requirement_names_are_canonicalised():
    from app.agents.requirements import parse_llm_requirements

    text = "Experience with Airflow/Flyte/Ray. A computer science degree. Fluent German."
    reqs = parse_llm_requirements(
        [
            {
                "name": "Airflow/Flyte/Ray",
                "type": "tech",
                "importance": "must",
                "quote": "Experience with Airflow/Flyte/Ray",
            },
            {
                "name": "computer science degree",
                "type": "degree",
                "importance": "nice",
                "quote": "A computer science degree",
            },
            {"name": "Fake", "type": "tech", "importance": "must", "quote": "not in the text"},
        ],
        text,
    )
    names = {r.name: r for r in reqs}
    assert "Apache Airflow" in names and names["Apache Airflow"].importance == "must"
    assert "Degree" in names and "Fake" not in names  # unquotable items are dropped (G2)


def test_compound_titles_match_each_side():
    from app.domain.titles import variants

    assert variants("Lead Data & AI Engineer") == [
        "Lead Data & AI Engineer",
        "Lead Data Engineer",
        "AI Engineer",
    ]
    assert title_matches("Senior AI Engineer (m/w/d)", ["Lead Data & AI Engineer"])
    assert title_matches("Data Engineer", ["Lead Data & AI Engineer"])
    assert not title_matches("Data Analyst", ["Lead Data & AI Engineer"])
