def test_health_ok(mock_client):
    r = mock_client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["mock_mode"] is True
    assert body["nebius_configured"] is False
    assert body["tavily_configured"] is False
    assert body["model"].startswith("nvidia/")


def test_health_reports_configured_keys(client_factory):
    client = client_factory(nebius_api_key="test-key", tavily_api_key="tvly-test")
    body = client.get("/health").json()
    assert body["nebius_configured"] is True
    assert body["tavily_configured"] is True


def test_openapi_lists_endpoints(mock_client):
    paths = mock_client.get("/openapi.json").json()["paths"]
    assert {"/health", "/api/cv", "/api/jobs/search"} <= set(paths)
