"""Mock mode (D18): fake Tavily and job boards; the real pipeline code runs on top of them.

Companies and URLs are fictional. Dates are relative to today, so freshness rules behave the
same every day. One job is closed (not on its board) and one is stale, to exercise checks.
"""

from datetime import date, timedelta
from typing import Any

from app.services.ats import Ats, BoardJob, BoardRef
from app.services.tavily_client import SearchResult


def _ago(days: int) -> date:
    return date.today() - timedelta(days=days)


_DE_TEXT = """About the role
You will build the data platform behind our energy marketplace.

What you'll do
• Design batch and streaming pipelines with Apache Airflow and Kafka
• Own data models in dbt and Snowflake

What you bring
• 3+ years of experience as a Data Engineer
• Strong Python and SQL skills
• Experience with AWS and Docker
• Fluent English; German B2 is required
• Good communication skills

Nice to have
• Kubernetes and Terraform
• Experience with Apache Spark

What we offer
• Hybrid work in Berlin, 30 days of vacation"""

_SR_TEXT = """We are looking for a Senior Data Engineer to scale our payments data.

Your profile
• 5+ years of experience with Python and Apache Spark
• Deep knowledge of SQL and PostgreSQL
• Experience with Google Cloud (BigQuery)
• English (fluent)

Nice to have
• Apache Airflow, dbt
• Mentoring junior engineers

Benefits
• Remote within Germany"""

_AE_TEXT = """As an Analytics Engineer you turn raw events into trusted metrics.

Requirements
• 2+ years in analytics or data engineering
• Excellent SQL and dbt
• Python for data work
• Experience with Looker or Tableau
• Stakeholder management across product and finance

Bonus
• Snowflake
• A/B testing experience"""

_BE_TEXT = """Join our core team building APIs for logistics.

What you bring
• 4+ years of backend experience with Go or Java
• REST APIs and gRPC, microservices
• PostgreSQL and Redis
• Docker and Kubernetes in production

Nice to have
• Kafka
• German (good)"""

_ML_TEXT = """You will ship machine learning models to production.

Qualifications
• 3+ years of experience with Python, PyTorch and scikit-learn
• Machine learning and MLOps practices
• Docker, AWS
• Master's degree in Computer Science or similar

Nice to have
• LLMs and NLP
• Kubernetes"""

_PM_TEXT = """Lead product discovery for our B2B platform.

What you bring
• 4+ years of product management
• Agile and roadmap ownership
• Excellent communication, stakeholder management
• German C1 and English C1"""


def _job(
    ats: Ats,
    slug: str,
    jid: str,
    title: str,
    company: str,
    loc: str,
    days: int,
    text: str,
    remote: bool = False,
    wt: str | None = "hybrid",
    domain: str | None = None,
) -> BoardJob:
    if ats == "greenhouse":
        url = f"https://job-boards.greenhouse.io/{slug}/jobs/{jid}"
    elif ats == "lever":
        url = f"https://jobs.lever.co/{slug}/{jid}"
    else:
        url = f"https://jobs.ashbyhq.com/{slug}/{jid}"
    return BoardJob(
        ats=ats,
        slug=slug,
        external_id=jid,
        url=url,
        title=title,
        company=company,  # type: ignore[arg-type]
        location_text=loc,
        country_code=None,
        remote=remote,
        workplace_type="remote" if remote else wt,
        posted_at=_ago(days),
        apply_url=url + ("/apply" if ats == "lever" else ""),
        text=text,
        own_domain=domain,
    )


def _boards() -> dict[tuple[str, str], list[BoardJob]]:
    return {
        ("greenhouse", "nordlichtdata"): [
            _job(
                "greenhouse",
                "nordlichtdata",
                "101",
                "Data Engineer",
                "Nordlicht Data",
                "Berlin, Germany",
                4,
                _DE_TEXT,
                domain="nordlicht-data.example",
            ),
            _job(
                "greenhouse",
                "nordlichtdata",
                "102",
                "Analytics Engineer",
                "Nordlicht Data",
                "Berlin, Germany",
                12,
                _AE_TEXT,
                domain="nordlicht-data.example",
            ),
            _job(
                "greenhouse",
                "nordlichtdata",
                "103",
                "Machine Learning Engineer",
                "Nordlicht Data",
                "Munich, Germany",
                20,
                _ML_TEXT,
                domain="nordlicht-data.example",
            ),
            _job(
                "greenhouse",
                "nordlichtdata",
                "199",
                "Data Engineer (2025)",
                "Nordlicht Data",
                "Berlin, Germany",
                220,
                _DE_TEXT,
                domain="nordlicht-data.example",
            ),
        ],
        ("lever", "havelpay"): [
            _job(
                "lever",
                "havelpay",
                "aa11",
                "Senior Data Engineer",
                "Havelpay",
                "Remote - Germany",
                2,
                _SR_TEXT,
                remote=True,
            ),
            _job("lever", "havelpay", "aa12", "Product Manager", "Havelpay", "Berlin", 8, _PM_TEXT),
        ],
        ("ashby", "spreeware"): [
            _job(
                "ashby",
                "spreeware",
                "b001",
                "Backend Engineer",
                "Spreeware",
                "Berlin",
                6,
                _BE_TEXT,
                wt="onsite",
            ),
            _job(
                "ashby",
                "spreeware",
                "b002",
                "Data Engineer",
                "Spreeware",
                "Hamburg, Germany",
                15,
                _SR_TEXT.replace("Senior Data Engineer", "Data Engineer"),
                wt="hybrid",
            ),
            _job(
                "ashby",
                "spreeware",
                "b003",
                "Data Platform Engineer",
                "Spreeware",
                "Berlin",
                30,
                _DE_TEXT,
                wt="hybrid",
            ),
        ],
    }


class FakeBoards:
    async def jobs(self, ref: BoardRef) -> list[BoardJob] | None:
        return _boards().get((ref.ats, ref.slug))

    async def aclose(self) -> None:
        return None


class FakeTavily:
    """Returns board URLs for any query, plus one link to a job that has since closed."""

    async def search(self, query: str, **_: Any) -> SearchResult:
        urls = [j.url for jobs in _boards().values() for j in jobs]
        urls.append("https://job-boards.greenhouse.io/nordlichtdata/jobs/150")  # closed
        return SearchResult(
            results=[
                {"url": u, "title": "Job", "content": "", "published_date": None} for u in urls
            ],
            credits=0,
        )
