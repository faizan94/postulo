"""The tokenized form: case and spelling never block a match (skills, titles, places)."""

import pytest

from app.agents.requirements import canonical_names
from app.domain.glossary import glossary
from app.domain.matching import match
from app.domain.normalize import fold, key, spelling_variants, title_tokens
from app.domain.places import JobLocation, places
from app.domain.titles import title_matches
from app.schemas.common import Evidence
from app.schemas.posting import Requirement
from app.schemas.profile import Profile, SkillItem
from app.scoring.summary import skill_summary

EV = Evidence(quote="x")


def test_fold_and_key():
    assert fold("  München  ") == "munchen"
    assert fold("Straße") == "strasse"
    assert key("Node.js") == key("Node JS") == key("NODEJS") == "nodejs"
    assert key("C++") == "c++" and key("C#") == "c#"
    assert spelling_variants("Zürich") == {"zürich", "zurich", "zuerich"}


def _status(cv_skill: str, job_skill: str) -> str:
    g = glossary()
    profile = Profile(skills=[SkillItem(name=g.canonical(cv_skill), type="tech", evidence=EV)])
    req = Requirement(name=job_skill, type="tech", importance="must", evidence=EV)
    return match(profile, [req])[0].status


@pytest.mark.parametrize(
    ("cv", "job"),
    [
        ("React", "REACT"),
        ("react", "React"),
        ("ReactJS", "React"),
        ("Node JS", "Node.js"),
        ("TypeScript", "Type Script"),
        ("Next JS", "Next.js"),
        ("C sharp", "C#"),
        ("Flyte", "flyte"),  # unknown to the glossary: still matched by key
        ("k8s", "Kubernetes"),
    ],
)
def test_skill_spellings_match(cv, job):
    assert _status(cv, job) == "have"


def test_longer_names_are_not_shortened():
    assert _status("React", "React Native") == "related"  # not "have"
    assert [n for n, _ in canonical_names("React Native", "tech")] == ["React Native"]
    assert [h.term.name for h in glossary().find("React Native and React")] == [
        "React Native",
        "React",
    ]


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("REACT", ["React"]),
        ("Vue.js/React", ["Vue", "React"]),
        ("Apache Airflow/Flyte/Ray", ["Apache Airflow"]),  # "/" = alternatives we know
        ("Python, SQL and dbt", ["Python", "SQL", "dbt"]),  # "," and "and" = all of them
        ("Docker", ["Docker"]),  # "or" inside a word never splits
        ("JavaScript (ES6)", ["JavaScript"]),
        ("Vector databases", ["Vector databases"]),  # unknown phrase kept as written
    ],
)
def test_llm_requirement_names(name, expected):
    assert [n for n, _ in canonical_names(name, "tech")] == expected


def test_summary_groups_spellings():
    g = glossary()
    profile = Profile(skills=[SkillItem(name="React", type="tech", evidence=EV)])
    jobs = [
        match(profile, [Requirement(name=n, type="tech", importance="must", evidence=EV)])
        for n in ("React", "REACT", "react.js")
    ]
    [item] = skill_summary(jobs)
    assert item.skill == g.canonical("React") and item.demand == 3


@pytest.mark.parametrize(
    ("job", "wanted"),
    [
        ("Softwareentwickler (m/w/d)", "Software Engineer"),
        ("Sr. ML Eng", "ML Engineer"),
        ("DevOps Engineer", "Dev Ops Engineer"),
        ("Machine Learning Engineer", "ML Engineer"),
        ("SENIOR REACT DEVELOPER", "React Developer"),
        ("Frontend-Entwickler:in", "Front-End Developer"),
        ("Datenanalyst", "Data Analyst"),
    ],
)
def test_title_variants_match(job, wanted):
    assert title_matches(job, [wanted])


def test_short_words_need_exact_match():
    assert not title_matches("Airline Engineer", ["AI Engineer"])
    assert title_tokens("Full-Stack Entwickler*in") == ["fullstack", "entwickler"]


@pytest.mark.parametrize(
    ("location", "search"),
    [
        ("Munchen, Germany", "Munich"),
        ("MÜNCHEN", "München"),
        ("Koln", "Cologne"),
        ("Zuerich", "Zurich"),
        ("Düsseldorf", "dusseldorf"),
    ],
)
def test_place_spellings_match(location, search):
    p = places()
    assert p.matches(JobLocation(location), p.resolve(search))


def test_typed_place_resolves_any_spelling():
    p = places()
    assert {p.resolve(x).name for x in ("münchen", "MUNICH", "Muenchen", "munchen")} == {"Munich"}
    assert p.search("koln")[0].name == "Cologne"
