import json

from app.cli import main
from tests.conftest import text_pdf


def test_cli_run_mock_writes_outputs(tmp_path, capsys):
    cv = tmp_path / "cv.pdf"
    cv.write_bytes(text_pdf())
    out = tmp_path / "output"
    code = main(
        [
            "run",
            str(cv),
            "--mock",
            "--location",
            "Germany",
            "--date",
            "2026-10-18",
            "--out",
            str(out),
        ]
    )
    assert code == 0
    run_dir = out / "2026-10-18"
    results = json.loads((run_dir / "results.json").read_text(encoding="utf-8"))
    assert results["mock"] is True and results["postings"]
    briefing = (run_dir / "briefing.md").read_text(encoding="utf-8")
    assert "# Postulo briefing - 2026-10-18" in briefing
    assert "Verdict" in briefing
    assert "[verify]" in capsys.readouterr().out


def test_cli_cv_mock_prints_profile(tmp_path, capsys):
    cv = tmp_path / "cv.pdf"
    cv.write_bytes(text_pdf())
    assert main(["cv", str(cv), "--mock"]) == 0
    assert json.loads(capsys.readouterr().out)["skills"]
