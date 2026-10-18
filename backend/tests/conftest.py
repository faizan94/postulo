from collections.abc import Callable, Iterator

import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.main import app


def make_settings(**overrides: object) -> Settings:
    """Settings that ignore .env and real keys, so tests never hit the network."""
    base: dict[str, object] = {
        "nebius_api_key": None,
        "tavily_api_key": None,
        "mock_mode": True,
    }
    base.update(overrides)
    return Settings(_env_file=None, **base)  # type: ignore[arg-type,call-arg]


def text_pdf(text: str = "Alex Example - Data Engineer. Python, SQL, dbt, Spark, AWS.") -> bytes:
    """A minimal one-page PDF with real extractable text (no external tools needed)."""
    stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode()
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
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


ClientFactory = Callable[..., TestClient]


@pytest.fixture
def client_factory() -> Iterator[ClientFactory]:
    def make(**overrides: object) -> TestClient:
        settings = make_settings(**overrides)
        app.dependency_overrides[get_settings] = lambda: settings
        return TestClient(app)

    yield make
    app.dependency_overrides.clear()


@pytest.fixture
def mock_client(client_factory: ClientFactory) -> TestClient:
    return client_factory(mock_mode=True)


@pytest.fixture
def live_client_no_keys(client_factory: ClientFactory) -> TestClient:
    return client_factory(mock_mode=False)
