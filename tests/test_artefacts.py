from __future__ import annotations

import pytest

from minerva_email_parser.service.extraction_service import ExtractionService

PLAIN_TEXT = (
    "Hi John,\n\n"
    "Check the report: https://example.com/reports/q3\n"
    "Contact support@example.com or call +1 (555) 019-2834.\n"
)

HTML = """
<html>
<head><title>Ignore this: https://ignored.example.com</title></head>
<body>
  <p>
    <a href="https://example.com/reports/q3">Project Dashboard</a>
    <a href="mailto:support@example.com">support@example.com</a>
    <a href="tel:+15550192834">+1 (555) 019-2834</a>
  </p>
  <img src="https://example.com/logo.png">
</body>
</html>
"""


@pytest.fixture
def extraction_service() -> ExtractionService:
    return ExtractionService()


def test_extract_artefacts_finds_links_emails_and_phone_numbers(
    extraction_service: ExtractionService,
) -> None:
    artefacts = extraction_service.extract_artefacts(PLAIN_TEXT, HTML)

    assert artefacts["links"]
    assert artefacts["phoneNumbers"]
    assert artefacts["emailAddresses"]


def test_link_found_in_both_plain_and_html_is_merged(extraction_service: ExtractionService) -> None:
    artefacts = extraction_service.extract_artefacts(PLAIN_TEXT, HTML)

    report_link = next(
        link for link in artefacts["links"] if link["href"] == "https://example.com/reports/q3"
    )
    assert report_link["source"] == "both"
    assert report_link["visible"] == "Project Dashboard"
    assert report_link["type"] == "https"
    assert report_link["domain"] == "example.com"


def test_html_only_image_src_has_no_visible_text_and_type_src(extraction_service: ExtractionService) -> None:
    artefacts = extraction_service.extract_artefacts(None, HTML)

    logo_link = next(link for link in artefacts["links"] if link["href"] == "https://example.com/logo.png")
    assert logo_link["source"] == "html"
    assert logo_link["visible"] is None
    assert logo_link["type"] == "src"


def test_head_tag_is_ignored_only_body_is_considered(extraction_service: ExtractionService) -> None:
    artefacts = extraction_service.extract_artefacts(None, HTML)

    hrefs = [link["href"] for link in artefacts["links"]]
    assert "https://ignored.example.com" not in hrefs


def test_email_address_gets_validated_and_domain_extracted(extraction_service: ExtractionService) -> None:
    artefacts = extraction_service.extract_artefacts(PLAIN_TEXT, HTML)

    email = next(e for e in artefacts["emailAddresses"] if e["value"] == "support@example.com")
    assert email["source"] == "both"
    assert email["isValid"] is True
    assert email["domain"] == "example.com"


def test_invalid_looking_email_is_flagged_but_still_reported(extraction_service: ExtractionService) -> None:
    artefacts = extraction_service.extract_artefacts("Reach me at not-an-email@@bad..domain", None)

    assert artefacts["emailAddresses"] == []


def test_phone_number_normalized_and_validated(extraction_service: ExtractionService) -> None:
    artefacts = extraction_service.extract_artefacts(PLAIN_TEXT, HTML)

    phone = artefacts["phoneNumbers"][0]
    assert phone["value"] == "+15550192834"
    assert phone["source"] == "both"
    # 555 numbers are the fictional range used in this test data — structurally
    # plausible (hence extracted) but not a real assigned/dialable number.
    assert phone["isValid"] is False
    # region_code_for_number can't attribute a region to a number it
    # considers invalid, e.g. this fictional 555 range.
    assert phone["region"] is None


def test_extract_artefacts_handles_missing_body(extraction_service: ExtractionService) -> None:
    artefacts = extraction_service.extract_artefacts(None, None)

    assert artefacts == {"links": [], "phoneNumbers": [], "emailAddresses": []}
