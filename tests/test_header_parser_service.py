from __future__ import annotations

import pytest

from minerva_email_parser.service.header_parser_service import HeaderParserService, ParsedAddress


@pytest.fixture
def header_parser() -> HeaderParserService:
    return HeaderParserService()


def test_parses_single_address_with_display_name(header_parser: HeaderParserService) -> None:
    addresses = header_parser.parse_address_header("From", "Jane Doe <jane.doe@example.com>")

    assert addresses == [
        ParsedAddress(
            display_name="Jane Doe",
            email="jane.doe@example.com",
            username="jane.doe",
            domain="example.com",
        )
    ]


def test_parses_multiple_addresses_from_a_list_header(header_parser: HeaderParserService) -> None:
    addresses = header_parser.parse_address_header(
        "To", 'John Smith <john@example.com>, "Support, Team" <support@example.com>'
    )

    assert [a.email for a in addresses] == ["john@example.com", "support@example.com"]
    assert addresses[1].display_name == "Support, Team"


def test_parses_bare_address_without_display_name(header_parser: HeaderParserService) -> None:
    addresses = header_parser.parse_address_header("Reply-To", "no-reply@example.com")

    assert addresses == [
        ParsedAddress(
            display_name="", email="no-reply@example.com", username="no-reply", domain="example.com"
        )
    ]


def test_returns_empty_list_for_empty_value(header_parser: HeaderParserService) -> None:
    assert header_parser.parse_address_header("From", "") == []


def test_skips_unparsable_garbage_value(header_parser: HeaderParserService) -> None:
    assert header_parser.parse_address_header("From", "not an email at all") == []


def test_is_address_header_is_case_insensitive_and_covers_resent_variants(
    header_parser: HeaderParserService,
) -> None:
    assert header_parser.is_address_header("From") is True
    assert header_parser.is_address_header("to") is True
    assert header_parser.is_address_header("Resent-Cc") is True
    assert header_parser.is_address_header("Subject") is False
    assert header_parser.is_address_header("X-Mailer") is False
