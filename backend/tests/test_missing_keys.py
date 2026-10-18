"""Without keys and MOCK_MODE=false, endpoints must return clear errors, not crash."""

from tests.conftest import text_pdf


def test_jobs_search_without_keys(live_client_no_keys):
    r = live_client_no_keys.post(
        "/api/jobs/search", json={"profile": {"skills": ["Python"]}, "preferences": {}}
    )
    assert r.status_code == 503
    err = r.json()["error"]
    assert err["code"] == "missing_api_key"
    assert "MOCK_MODE" in err["message"]


def test_cv_without_nebius_key(live_client_no_keys):
    long_text = "Alex Example, Data Engineer with Python, SQL, dbt, Spark and AWS experience."
    r = live_client_no_keys.post(
        "/api/cv", files={"file": ("cv.pdf", text_pdf(long_text), "application/pdf")}
    )
    assert r.status_code == 503
    assert "NEBIUS_API_KEY" in r.json()["error"]["message"]


def test_cv_without_text(live_client_no_keys):
    r = live_client_no_keys.post(
        "/api/cv", files={"file": ("cv.pdf", text_pdf("hi"), "application/pdf")}
    )
    assert r.status_code == 400
