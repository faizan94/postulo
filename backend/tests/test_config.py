import pytest

from app.config import Settings
from app.services.llm import extract_json, reasoning_extra_body
from tests.conftest import make_settings

ENV_VARS = [
    "NEBIUS_API_KEY",
    "NEBIUS_BASE_URL",
    "NEMOTRON_MODEL",
    "NEMOTRON_FAST_MODEL",
    "TAVILY_API_KEY",
    "MOCK_MODE",
    "CORS_ORIGINS",
    "LOG_LEVEL",
    "MAX_POSTINGS",
    "DATABASE_URL",
]


@pytest.fixture
def clean_env(monkeypatch):
    for var in ENV_VARS:
        monkeypatch.delenv(var, raising=False)
    return monkeypatch


def test_defaults(clean_env):
    s = Settings(_env_file=None)  # type: ignore[call-arg]
    assert s.nebius_base_url == "https://api.tokenfactory.nebius.com/v1/"
    assert s.nemotron_model == "nvidia/Nemotron-3.5-Super-VL"
    assert s.nemotron_fast_model == "nvidia/Nemotron-3_5-Lightning"
    assert s.database_url.startswith("sqlite+aiosqlite")
    assert s.mock_mode is False
    assert s.nebius_api_key is None
    assert s.cors_origin_list == ["http://localhost:3000"]
    assert s.log_level == "INFO"


def test_env_overrides(clean_env):
    clean_env.setenv("MOCK_MODE", "true")
    clean_env.setenv("NEMOTRON_MODEL", "nvidia/some-other-model")
    clean_env.setenv("CORS_ORIGINS", "http://localhost:3000, https://postulo.example")
    clean_env.setenv("TAVILY_API_KEY", "tvly-test")
    s = Settings(_env_file=None)  # type: ignore[call-arg]
    assert s.mock_mode is True
    assert s.nemotron_model == "nvidia/some-other-model"
    assert s.cors_origin_list == ["http://localhost:3000", "https://postulo.example"]
    assert s.tavily_configured is True


def test_make_settings_ignores_keys():
    s = make_settings()
    assert not s.nebius_configured and not s.tavily_configured


@pytest.mark.parametrize(
    ("mode", "expected"),
    [
        ("off", {"enable_thinking": False}),
        ("on", {"enable_thinking": True}),
        ("medium", {"enable_thinking": True, "medium_effort": True}),
    ],
)
def test_reasoning_toggle(mode, expected):
    assert reasoning_extra_body(mode) == {"chat_template_kwargs": expected}


@pytest.mark.parametrize(
    "text",
    [
        '{"a": 1}',
        '```json\n{"a": 1}\n```',
        '<think>hmm {"b": 2}</think>Here you go: {"a": 1} hope it helps',
    ],
)
def test_extract_json(text):
    assert extract_json(text) == {"a": 1}


def test_extract_json_raises():
    with pytest.raises(ValueError):
        extract_json("no json here")
