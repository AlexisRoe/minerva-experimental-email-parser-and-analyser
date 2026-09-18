from __future__ import annotations

from pathlib import Path

from minerva_email_parser.use_case_loader import discover_use_cases

USE_CASE_DIR = Path(__file__).resolve().parent.parent / "src" / "minerva_email_parser" / "use-case"
ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"


def _base_parser():  # noqa: ANN202
    (use_case,) = [uc for uc in discover_use_cases(USE_CASE_DIR) if uc.name == "base-parser"]
    return use_case


def test_base_parser_extracts_headers_body_and_attachments(tmp_path: Path, monkeypatch: object) -> None:
    use_case = _base_parser()
    monkeypatch.setattr(use_case.module, "ATTACHMENTS_BUCKET_DIR", tmp_path)  # type: ignore[attr-defined]

    with (ASSETS_DIR / "base.eml").open("rb") as stream:
        result = use_case.run(stream)

    assert {"key": "Subject", "value": "Project Update & Q3 Summary"} in result["headers"]

    assert result["body"]["plainText"] is not None
    assert "Hi John" in result["body"]["plainText"]
    assert result["body"]["html"] is not None

    assert len(result["attachments"]) == 1
    attachment = result["attachments"][0]
    assert attachment["fileName"] == "icon.png"
    assert attachment["contentType"] == "image/png"
    assert attachment["binary"] is True
    assert attachment["sizeInBytes"] > 0
    assert "payload" not in attachment

    # base.eml's attachment has no content-id, so an internal id is generated
    # and used as the storage key instead.
    assert attachment["id"] is None
    assert attachment["internalId"]
    stored_files = list(tmp_path.glob(f"{attachment['internalId']}.*"))
    assert len(stored_files) == 1
    assert stored_files[0].read_bytes()
