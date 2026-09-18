from __future__ import annotations

import re
from typing import Any, Literal, cast
from urllib.parse import urlparse

import phonenumbers
from bs4 import BeautifulSoup
from email_validator import EmailNotValidError, validate_email
from urlextract import URLExtract

ArtefactSource = Literal["plain-text", "html", "both"]

# Numbers without a leading `+` are ambiguous without a country to assume —
# this only affects national-format matches; `+`-prefixed numbers are parsed
# regardless of region.
DEFAULT_PHONE_NUMBER_REGION = "US"

EMAIL_ADDRESS_PATTERN = re.compile(r"[A-Za-z0-9!#$%&'*+/=?^_`{|}~.-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+")

# Tags that reference an external resource, and the attribute that holds it.
LINK_TAG_ATTRIBUTES = {
    "a": "href",
    "area": "href",
    "link": "href",
    "img": "src",
    "script": "src",
    "iframe": "src",
    "source": "src",
    "frame": "src",
    "embed": "src",
}


class ExtractionService:
    """Extracts links, phone numbers, and email addresses from an email body."""

    def __init__(self) -> None:
        self._url_extractor = URLExtract()

    def extract_artefacts(self, plain_text: str | None, html: str | None) -> dict[str, Any]:
        """Extract links, phone numbers, and email addresses from an email body.

        Only the `<body>` of the HTML is considered (falling back to the whole
        document if there's no `<body>` tag, e.g. for HTML fragments).

        Args:
            plain_text: The email's plain-text body, or `None` if it has none.
            html: The email's HTML body, or `None` if it has none.

        Returns:
            A dict with `links`, `phoneNumbers`, and `emailAddresses` keys.
        """
        html_text: str | None = None
        html_links: list[dict[str, Any]] = []
        if html:
            body = BeautifulSoup(html, "html.parser")
            body = body.find("body") or body
            html_text = body.get_text(separator=" ")
            html_links = self._extract_html_links(body)

        plain_links = self._extract_plain_text_links(plain_text) if plain_text else []

        return {
            "links": self._merge_links(html_links, plain_links),
            "phoneNumbers": self._extract_phone_numbers(plain_text, html_text),
            "emailAddresses": self._extract_email_addresses(plain_text, html_text),
        }

    def _extract_html_links(self, body: Any) -> list[dict[str, Any]]:
        links: list[dict[str, Any]] = []
        for tag_name, attribute in LINK_TAG_ATTRIBUTES.items():
            for tag in body.find_all(tag_name):
                href = tag.get(attribute)
                if not href:
                    continue
                href = href.strip()
                visible = tag.get_text(strip=True) or None if tag.name == "a" else None
                links.append(
                    {
                        "source": "html",
                        "type": "src" if attribute == "src" else (urlparse(href).scheme or "relative"),
                        "visible": visible,
                        "href": href,
                        "domain": urlparse(href).netloc or None,
                    }
                )
        return links

    def _extract_plain_text_links(self, plain_text: str) -> list[dict[str, Any]]:
        links: list[dict[str, Any]] = []
        # `only_unique=True` (no `get_indices`) always returns plain strings;
        # the library's overloads just don't encode that.
        urls = cast("list[str]", self._url_extractor.find_urls(plain_text, only_unique=True))
        for url in urls:
            links.append(
                {
                    "source": "plain-text",
                    "type": urlparse(url).scheme or "relative",
                    "visible": None,
                    "href": url,
                    "domain": urlparse(url).netloc or None,
                }
            )
        return links

    def _merge_links(
        self, html_links: list[dict[str, Any]], plain_links: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        merged: dict[str, dict[str, Any]] = {}
        for link in [*html_links, *plain_links]:
            href = link["href"]
            existing = merged.get(href)
            if existing is None:
                merged[href] = dict(link)
                continue
            if existing["source"] != link["source"]:
                existing["source"] = "both"
            if existing["visible"] is None and link["visible"] is not None:
                existing["visible"] = link["visible"]
        return list(merged.values())

    def _extract_phone_numbers(self, plain_text: str | None, html_text: str | None) -> list[dict[str, Any]]:
        plain_numbers = self._find_phone_numbers(plain_text) if plain_text else set()
        html_numbers = self._find_phone_numbers(html_text) if html_text else set()

        results: list[dict[str, Any]] = []
        for value in sorted(plain_numbers | html_numbers):
            source = self._resolve_source(value in plain_numbers, value in html_numbers)
            parsed = phonenumbers.parse(value, None)
            results.append(
                {
                    "source": source,
                    "value": value,
                    "isValid": phonenumbers.is_valid_number(parsed),
                    "region": phonenumbers.region_code_for_number(parsed),
                }
            )
        return results

    def _find_phone_numbers(self, text: str) -> set[str]:
        # POSSIBLE (rather than the default VALID) leniency so structurally
        # plausible numbers are still reported even when not (or no longer)
        # assigned/dialable — `isValid` on the result reflects that separately.
        matcher = phonenumbers.PhoneNumberMatcher(
            text, DEFAULT_PHONE_NUMBER_REGION, leniency=phonenumbers.Leniency.POSSIBLE
        )
        return {
            phonenumbers.format_number(match.number, phonenumbers.PhoneNumberFormat.E164) for match in matcher
        }

    def _extract_email_addresses(self, plain_text: str | None, html_text: str | None) -> list[dict[str, Any]]:
        plain_emails = self._find_email_addresses(plain_text) if plain_text else set()
        html_emails = self._find_email_addresses(html_text) if html_text else set()

        results: list[dict[str, Any]] = []
        for value in sorted(plain_emails | html_emails):
            source = self._resolve_source(value in plain_emails, value in html_emails)
            results.append(
                {
                    "source": source,
                    "value": value,
                    "isValid": self._is_valid_email(value),
                    "domain": value.rsplit("@", 1)[-1],
                }
            )
        return results

    def _find_email_addresses(self, text: str) -> set[str]:
        return set(EMAIL_ADDRESS_PATTERN.findall(text))

    def _is_valid_email(self, address: str) -> bool:
        try:
            validate_email(address, check_deliverability=False)
        except EmailNotValidError:
            return False
        return True

    def _resolve_source(self, found_in_plain: bool, found_in_html: bool) -> ArtefactSource:
        if found_in_plain and found_in_html:
            return "both"
        return "plain-text" if found_in_plain else "html"
