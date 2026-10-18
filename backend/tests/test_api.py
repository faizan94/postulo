"""API end to end in mock mode (fake Tavily + boards over a real SQLite DB, D18)."""

import json

from tests.conftest import CV_TEXT, confirmed_cv, docx_bytes, login, text_pdf, wait_done

BERLIN = {"kind": "city", "name": "Berlin", "country_code": "DE"}


def test_login_same_name_same_user_and_logout(mock_client):
    h1 = login(mock_client, "Alex")
    h2 = login(mock_client, "  alex ")
    me1 = mock_client.get("/api/me", headers=h1).json()
    me2 = mock_client.get("/api/me", headers=h2).json()
    assert me1["user"]["id"] == me2["user"]["id"] and me1["has_cv"] is False
    assert mock_client.post("/api/auth/logout", headers=h1).status_code == 204
    r = mock_client.get("/api/me", headers=h1)
    assert r.status_code == 401 and r.json()["error"]["code"] == "unauthorized"


def test_requires_auth_and_valid_name(mock_client):
    assert mock_client.get("/api/me").status_code == 401
    assert mock_client.post("/api/auth/login", json={"name": "x"}).status_code == 400


def test_places_endpoint(mock_client):
    names = [p["name"] for p in mock_client.get("/api/places").json()]
    assert "Berlin" in names and "Remote" in names
    assert mock_client.get("/api/places?q=ham").json()[0]["name"] == "Hamburg"


def test_cv_upload_pdf_docx_and_confirm(mock_client):
    h = login(mock_client)
    pdf = mock_client.post(
        "/api/cv", files={"file": ("cv.pdf", text_pdf(CV_TEXT), "application/pdf")}, headers=h
    )
    assert pdf.status_code == 200, pdf.text
    assert "alex@example.com" not in pdf.json()["text"]
    docx = mock_client.post(
        "/api/cv",
        files={"file": ("cv.docx", docx_bytes(CV_TEXT), "application/octet-stream")},
        headers=h,
    )
    assert docx.status_code == 200
    body = confirmed_cv(mock_client, h)
    assert body["suggested"]["titles"][0] == "Data Engineer"
    assert body["suggested"]["place"]["name"] == "Berlin"
    assert {s["name"] for s in body["profile"]["skills"]} >= {"Python", "SQL"}
    versions = mock_client.get("/api/cv", headers=h).json()
    assert len(versions) == 1 and versions[0]["status"] == "confirmed"  # drafts are not listed
    bad = mock_client.post("/api/cv", files={"file": ("x.doc", b"\xd0\xcf", "x")}, headers=h)
    assert bad.status_code == 400


def test_search_end_to_end_with_stream_detail_how_and_rerun(mock_client):
    h = login(mock_client)
    cv = confirmed_cv(mock_client, h)
    r = mock_client.post(
        "/api/searches",
        headers=h,
        json={
            "cv_version_id": cv["cv_version"]["id"],
            "titles": ["Data Engineer"],
            "places": [BERLIN],
        },
    )
    assert r.status_code == 200, r.text
    sid = r.json()["search_id"]
    detail = wait_done(mock_client, sid, h)
    assert detail["status"] == "done", detail
    titles = [c["title"] for c in detail["results"]]
    assert titles and all("Engineer" in t for t in titles)
    assert "Data Engineer (2025)" not in titles  # stale job dropped quietly
    first = detail["results"][0]
    assert first["match"]["value"] is not None and first["company_score"]["band"] != "pending"
    assert detail["skill_summary"] and detail["learn_next"]
    values = [c["match"]["value"] for c in detail["results"] if not c["match"]["thin"]]
    assert values == sorted(values, reverse=True)  # D16

    # defaults saved from the search (D11)
    me = mock_client.get("/api/me", headers=h).json()
    assert me["user"]["default_titles"] == ["Data Engineer"] and me["latest_search_id"] == sid

    # finished search: the stream sends a snapshot and done, then closes
    with mock_client.stream("GET", f"/api/searches/{sid}/events", headers=h) as resp:
        events = [json.loads(line[6:]) for line in resp.iter_lines() if line.startswith("data: ")]
    assert [e["type"] for e in events] == ["snapshot", "done"]

    # job detail: full text, apply link, all skills
    pid = first["posting_id"]
    job = mock_client.get(f"/api/postings/{pid}?search_id={sid}", headers=h).json()
    assert job["full_text"] and job["apply_url"].startswith("https://") and job["skills"]

    # trace view: trace and quiet drops (closed + stale)
    how = mock_client.get(f"/api/how/{sid}", headers=h).json()
    reasons = " ".join(d["reason"] for d in how["dropped"])
    assert "closed" in reasons and "stale" in reasons and how["trace"]

    # rerun: identical scores (D6)
    sid2 = mock_client.post(f"/api/searches/{sid}/rerun", headers=h).json()["search_id"]
    detail2 = wait_done(mock_client, sid2, h)
    scores = lambda d: {c["title"] + c["company"]: c["match"]["value"] for c in d["results"]}  # noqa: E731
    assert scores(detail2) == scores(detail)
    assert len(mock_client.get("/api/searches", headers=h).json()) == 2


def test_live_stream_while_running(mock_client):
    h = login(mock_client)
    cv = confirmed_cv(mock_client, h)
    sid = mock_client.post(
        "/api/searches",
        headers=h,
        json={
            "cv_version_id": cv["cv_version"]["id"],
            "titles": ["Data Engineer"],
            "places": [BERLIN],
        },
    ).json()["search_id"]
    with mock_client.stream("GET", f"/api/searches/{sid}/events", headers=h) as resp:
        types = [
            json.loads(line[6:])["type"] for line in resp.iter_lines() if line.startswith("data: ")
        ]
    assert types[0] == "snapshot" and types[-1] in ("done",)


def test_other_users_cannot_see_searches_and_delete_me(mock_client):
    h = login(mock_client, "Alex")
    cv = confirmed_cv(mock_client, h)
    sid = mock_client.post(
        "/api/searches",
        headers=h,
        json={
            "cv_version_id": cv["cv_version"]["id"],
            "titles": ["Data Engineer"],
            "places": [BERLIN],
        },
    ).json()["search_id"]
    wait_done(mock_client, sid, h)
    other = login(mock_client, "Sam")
    assert mock_client.get(f"/api/searches/{sid}", headers=other).status_code == 404
    assert mock_client.get(f"/api/how/{sid}", headers=other).status_code == 404
    assert mock_client.delete("/api/me", headers=h).status_code == 204
    assert mock_client.get("/api/me", headers=h).status_code == 401
    h_again = login(mock_client, "Alex")  # same name creates a fresh, empty account
    assert mock_client.get("/api/searches", headers=h_again).json() == []


def test_search_needs_confirmed_cv(mock_client):
    h = login(mock_client)
    draft = mock_client.post("/api/cv", data={"text": CV_TEXT}, headers=h).json()
    r = mock_client.post(
        "/api/searches",
        headers=h,
        json={
            "cv_version_id": draft["cv_version_id"],
            "titles": ["Data Engineer"],
            "places": [BERLIN],
        },
    )
    assert r.status_code == 400


def test_real_mode_without_tavily_key_is_a_clean_503(client_factory):
    client = client_factory(mock_mode=False)
    h = login(client)
    cv = confirmed_cv(client, h)
    r = client.post(
        "/api/searches",
        headers=h,
        json={
            "cv_version_id": cv["cv_version"]["id"],
            "titles": ["Data Engineer"],
            "places": [BERLIN],
        },
    )
    assert r.status_code == 503 and "TAVILY_API_KEY" in r.json()["error"]["message"]
