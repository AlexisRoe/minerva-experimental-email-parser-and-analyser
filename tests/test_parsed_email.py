from __future__ import annotations

from pathlib import Path

from minerva_email_parser.models.parsed_email_model import ParsedEmail
from minerva_email_parser.use_case_loader import discover_use_cases

USE_CASE_DIR = Path(__file__).resolve().parent.parent / "src" / "minerva_email_parser" / "use-case"
ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"


def test_base_parser_output_matches_parsed_email_schema(tmp_path: Path, monkeypatch: object) -> None:
    (use_case,) = [uc for uc in discover_use_cases(USE_CASE_DIR) if uc.name == "base-parser"]
    monkeypatch.setattr(use_case.module, "ATTACHMENTS_BUCKET_DIR", tmp_path)  # type: ignore[attr-defined]

    with (ASSETS_DIR / "base-extended.eml").open("rb") as stream:
        result = use_case.run(stream)

    parsed = ParsedEmail.model_validate(result)

    assert parsed.attachments
    assert parsed.headers
