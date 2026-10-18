import io
import time
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest
from docx import Document
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.main import app


def make_settings(**overrides: object) -> Settings:
    """Settings that ignore .env and real keys, so tests never hit the network."""
    base: dict[str, object] = {
        "nebius_api_key": None,
        "tavily_api_key": None,
        "mock_mode": True,
        "database_url": "sqlite+aiosqlite:///:memory:",
    }
    base.update(overrides)
    return Settings(_env_file=None, **base)  # type: ignore[arg-type,call-arg]


CV_TEXT = """Alex Example
Berlin, Germany
alex@example.com | +49 151 2345 6789
Geburtsdatum: 01.01.1990

Experience
Data Engineer, Nordwind GmbH, 03/2020 - present
Built pipelines with Python, SQL, Apache Airflow and dbt on AWS. Docker in production.
Junior Data Analyst, Seeblick AG, 2018 - 2020
Dashboards in Tableau, SQL, communication with stakeholders.

Education
M.Sc. Computer Science, TU Berlin, 2016 - 2018

Languages
English (fluent), German B2
"""


def text_pdf(text: str) -> bytes:
    """A minimal multi-line PDF with real extractable text (no external tools needed)."""
    lines = [ln.replace("(", "[").replace(")", "]") for ln in text.splitlines()]
    ops = ["BT /F1 10 Tf 50 800 Td 12 TL"] + [f"({ln}) Tj T*" for ln in lines] + ["ET"]
    stream = "\n".join(ops).encode("latin-1", "replace")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 842] "
        b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % i + obj + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    for off in offsets:
        out += b"%010d 00000 n \n" % off
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n" % (len(objects) + 1, xref)
    out += b"%%EOF\n"
    return bytes(out)


def docx_bytes(text: str) -> bytes:
    doc = Document()
    for line in text.splitlines():
        doc.add_paragraph(line)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


ClientFactory = Callable[..., TestClient]


@pytest.fixture
def client_factory(tmp_path: Path) -> Iterator[ClientFactory]:
    clients: list[TestClient] = []

    def make(**overrides: object) -> TestClient:
        overrides.setdefault("database_url", f"sqlite+aiosqlite:///{tmp_path.as_posix()}/t.db")
        settings = make_settings(**overrides)
        app.dependency_overrides[get_settings] = lambda: settings
        client = TestClient(app)
        client.__enter__()  # run the lifespan (DB, event bus, runner)
        clients.append(client)
        return client

    yield make
    for c in clients:
        c.__exit__(None, None, None)
    app.dependency_overrides.clear()


@pytest.fixture
def mock_client(client_factory: ClientFactory) -> TestClient:
    return client_factory(mock_mode=True)


def login(client: TestClient, name: str = "Alex") -> dict[str, str]:
    r = client.post("/api/auth/login", json={"name": name})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


def confirmed_cv(
    client: TestClient, headers: dict[str, str], text: str = CV_TEXT
) -> dict[str, Any]:
    draft = client.post("/api/cv", data={"text": text}, headers=headers)
    assert draft.status_code == 200, draft.text
    body = draft.json()
    r = client.put(f"/api/cv/{body['cv_version_id']}", json={"text": body["text"]}, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()  # type: ignore[no-any-return]


def wait_done(client: TestClient, search_id: int, headers: dict[str, str]) -> dict[str, Any]:
    for _ in range(200):
        r = client.get(f"/api/searches/{search_id}", headers=headers)
        assert r.status_code == 200, r.text
        if r.json()["status"] in ("done", "failed"):
            return r.json()  # type: ignore[no-any-return]
        time.sleep(0.05)
    raise AssertionError("search did not finish")
