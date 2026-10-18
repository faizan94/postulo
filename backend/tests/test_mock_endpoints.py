from tests.conftest import text_pdf


def test_cv_upload_mock(mock_client):
    r = mock_client.post(
        "/api/cv",
        files={"file": ("cv.pdf", text_pdf(), "application/pdf")},
        data={"prompt": "Data roles, Berlin"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["mock"] is True
    assert body["cv_text_chars"] > 0
    assert body["profile"]["skills"]


def test_cv_upload_rejects_non_pdf(mock_client):
    r = mock_client.post("/api/cv", files={"file": ("cv.txt", b"hello", "text/plain")})
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "bad_input"


def test_jobs_search_mock(mock_client):
    profile = mock_client.post(
        "/api/cv", files={"file": ("cv.pdf", text_pdf(), "application/pdf")}
    ).json()["profile"]
    r = mock_client.post(
        "/api/jobs/search",
        json={"profile": profile, "preferences": {"location": "Berlin", "prompt": "data"}},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["mock"] is True
    assert 5 <= len(body["postings"]) <= 10
    assert body["rejected"], "mock data should show removed ghost jobs"
    assert body["trace"]
    for p in body["postings"]:
        assert 0 <= p["score"] <= 5
        assert set(p["verified"]) == {"company_exists", "posting_live", "recent"}
        assert p["skills"]
        assert {s["status"] for s in p["skills"]} <= {"gold", "orange", "red"}
        assert p["url"].startswith("https://")


def test_jobs_search_validates_location(mock_client):
    r = mock_client.post(
        "/api/jobs/search", json={"profile": {}, "preferences": {"location": "Mars"}}
    )
    assert r.status_code == 422


def test_max_postings_respected(client_factory):
    client = client_factory(mock_mode=True, max_postings=3)
    r = client.post("/api/jobs/search", json={"profile": {}, "preferences": {}})
    assert len(r.json()["postings"]) == 3
