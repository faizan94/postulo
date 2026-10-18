"""Realistic fake data for MOCK_MODE=true, so the frontend works without API keys.

All companies and URLs here are fictional.
"""

from datetime import UTC, datetime, timedelta

from app.models.schemas import (
    AgentStep,
    Posting,
    Preferences,
    Profile,
    RejectedPosting,
    SearchResponse,
    Skill,
    VerifiedFlags,
)

LIVE = VerifiedFlags(company_exists=True, posting_live=True, recent=True)


def mock_profile() -> Profile:
    return Profile(
        name="Alex Example",
        headline="Data Engineer",
        summary="Data engineer with 4 years building batch and streaming pipelines in Python.",
        skills=["Python", "SQL", "dbt", "Apache Spark", "AWS", "Docker", "PostgreSQL", "Git"],
        years=4,
        languages=["English C2", "German B1"],
        target_roles=["Data Engineer", "Analytics Engineer"],
        location_pref="Berlin",
    )


def _days_ago(n: int) -> str:
    return (datetime.now(UTC) - timedelta(days=n)).date().isoformat()


def _s(name: str, status: str, note: str | None = None) -> Skill:
    return Skill(name=name, status=status, note=note)  # type: ignore[arg-type]


def _postings(city: str) -> list[Posting]:
    return [
        Posting(
            title="Senior Data Engineer",
            company="Spreewald Analytics",
            url="https://jobs.example.com/spreewald-analytics/senior-data-engineer-4821",
            posted=_days_ago(3),
            location=f"{city} (hybrid)",
            source="greenhouse.io",
            verified=LIVE,
            score=4.5,
            skills=[
                _s("Python", "gold"),
                _s("SQL", "gold"),
                _s("dbt", "gold"),
                _s("Apache Spark", "gold"),
                _s("AWS", "gold"),
                _s("Airflow", "orange", "Listed under 'nice to have'"),
                _s("Kafka", "orange"),
            ],
            why="Matches 5/7 skills; quoted requirement: '3+ years building production "
            "data pipelines in Python and SQL'.",
        ),
        Posting(
            title="Analytics Engineer",
            company="Kiezkasse",
            url="https://jobs.example.com/kiezkasse/analytics-engineer-1177",
            posted=_days_ago(6),
            location=city,
            source="jobs.lever.co",
            verified=LIVE,
            score=4.0,
            skills=[
                _s("SQL", "gold"),
                _s("dbt", "gold"),
                _s("Python", "gold"),
                _s("Looker", "orange", "BI tool, quick to learn"),
                _s("Data modelling", "gold"),
                _s("Fintech domain", "orange"),
            ],
            why="Strong dbt and SQL overlap; quoted requirement: 'you own our dbt models "
            "end to end'.",
        ),
        Posting(
            title="Data Platform Engineer",
            company="Havelwerk Mobility",
            url="https://jobs.example.com/havelwerk/data-platform-engineer-903",
            posted=_days_ago(9),
            location=f"{city} or remote (EU)",
            source="jobs.ashbyhq.com",
            verified=LIVE,
            score=3.5,
            skills=[
                _s("Python", "gold"),
                _s("Kubernetes", "orange"),
                _s("Terraform", "orange"),
                _s("AWS", "gold"),
                _s("Docker", "gold"),
                _s("Kafka", "red", "'Hands-on Kafka in production is a must'"),
            ],
            why="Good infra overlap, but Kafka is a hard requirement; quoted requirement: "
            "'hands-on Kafka in production is a must'.",
        ),
        Posting(
            title="Machine Learning Engineer (Data)",
            company="Lindenblatt Health",
            url="https://jobs.example.com/lindenblatt/ml-engineer-data-55",
            posted=_days_ago(12),
            location=city,
            source="jobs.personio.de",
            verified=LIVE,
            score=3.0,
            skills=[
                _s("Python", "gold"),
                _s("SQL", "gold"),
                _s("PyTorch", "red", "Core of the role"),
                _s("MLOps", "orange"),
                _s("German C1", "red", "'Fluent German (C1) required'"),
            ],
            why="Data skills fit, but the ML stack and German C1 are gaps; quoted "
            "requirement: 'fluent German (C1) required'.",
        ),
        Posting(
            title="Junior BI Developer",
            company="Tempelhof Logistics",
            url="https://jobs.example.com/tempelhof-logistics/bi-developer-310",
            posted=_days_ago(15),
            location=city,
            source="join.com",
            verified=LIVE,
            score=3.0,
            skills=[
                _s("SQL", "gold"),
                _s("Power BI", "orange"),
                _s("Excel", "gold"),
                _s("German B2", "orange", "You have B1"),
            ],
            why="Easy fit but below your level; quoted requirement: 'first experience with "
            "SQL and reporting'.",
        ),
        Posting(
            title="Staff Data Engineer",
            company="Nordlicht Energy",
            url="https://jobs.example.com/nordlicht-energy/staff-data-engineer-77",
            posted=_days_ago(20),
            location=f"{city} (on-site)",
            source="myworkdayjobs.com",
            verified=LIVE,
            score=2.5,
            skills=[
                _s("Python", "gold"),
                _s("Apache Spark", "gold"),
                _s("8+ years experience", "red", "You have 4"),
                _s("Team leadership", "red"),
                _s("Azure", "orange"),
            ],
            why="Tech fits, seniority does not yet; quoted requirement: '8+ years in data "
            "engineering, 2+ leading teams'.",
        ),
    ]


def mock_search(profile: Profile, prefs: Preferences, max_postings: int) -> SearchResponse:
    city = {"Berlin": "Berlin", "Germany": "Munich", "World": "Remote"}[prefs.location]
    postings = _postings(city)[:max_postings]
    return SearchResponse(
        profile=profile,
        postings=postings,
        rejected=[
            RejectedPosting(
                title="Data Engineer",
                company="Ghostline Media",
                url="https://jobs.example.com/ghostline/data-engineer-1",
                reason="page says 'no longer accepting applications'",
            ),
            RejectedPosting(
                title="Senior Python Developer",
                company="Evergreen Reposts",
                url="https://jobs.example.com/evergreen/python-dev-9",
                reason="older than 45 days (likely a repost or ghost job)",
            ),
        ],
        trace=[
            AgentStep(agent="orchestrator", message="Planned search for Data Engineer roles"),
            AgentStep(
                agent="search",
                message=f"Tavily: 3 queries, {len(postings) + 2} postings found",
                duration_ms=1840,
            ),
            AgentStep(
                agent="verify",
                message=f"{len(postings)} verified, 2 ghost jobs removed",
                duration_ms=2310,
            ),
            AgentStep(agent="score", message=f"Scored {len(postings)} postings", duration_ms=6120),
            AgentStep(agent="orchestrator", message="Ranked results by fit"),
        ],
        mock=True,
    )
