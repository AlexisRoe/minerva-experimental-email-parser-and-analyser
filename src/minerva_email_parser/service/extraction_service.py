from __future__ import annotations

import ipaddress
import re
from typing import Any, Literal, cast
from urllib.parse import urlparse

import phonenumbers
from bs4 import BeautifulSoup
from email_validator import EmailNotValidError, validate_email
from urlextract import URLExtract

ArtefactSource = Literal["plain-text", "html", "both"]

# Characters that can legally appear inside an IPv4/IPv6 literal, a bracketed
# IPv6 literal with a port, or a CIDR suffix.
IP_CANDIDATE_CHARS = set("0123456789abcdefABCDEF.:/[]")

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

    def extract_artefacts(
        self, headers: list[dict[str, str]] | None, plain_text: str | None, html: str | None
    ) -> dict[str, Any]:
        """Extract links, phone numbers, email addresses, and IPs from an email.

        Links, phone numbers, and email addresses only consider the body:
        the plain-text body and the `<body>` of the HTML (falling back to
        the whole document if there's no `<body>` tag, e.g. for HTML
        fragments). IP addresses also consider the raw headers, since
        received-chain/originating-IP evidence lives there. Attachment
        content is never considered.

        Args:
            headers: The email's raw headers (`key`/`value` pairs), or `None`.
            plain_text: The email's plain-text body, or `None` if it has none.
            html: The email's HTML body, or `None` if it has none.

        Returns:
            A dict with `links`, `phoneNumbers`, `emailAddresses`, and `ipAddresses` keys.
        """
        html_text: str | None = None
        html_links: list[dict[str, Any]] = []

        if html:
            body = BeautifulSoup(html, "html.parser")
            body = body.find("body") or body
            html_text = body.get_text(separator=" ")
            html_links = self._extract_html_links(body)

        plain_links = self._extract_plain_text_links(plain_text) if plain_text else []
        header_text = self._headers_to_text(headers) if headers else None

        return {
            "links": self._merge_links(html_links, plain_links),
            "phoneNumbers": self._extract_phone_numbers(plain_text, html_text),
            "emailAddresses": self._extract_email_addresses(plain_text, html_text),
            "ipAddresses": self._extract_ip_addresses(header_text, plain_text, html_text),
        }

    def _headers_to_text(self, headers: list[dict[str, str]]) -> str:
        return "\n".join(f"{header['key']}: {header['value']}" for header in headers)

    def _extract_html_links(self, body: Any) -> list[dict[str, Any]]:
        links: list[dict[str, Any]] = []

        # A single traversal over every relevant tag, rather than one
        # `find_all` (and full tree walk) per tag name.
        for tag in body.find_all(list(LINK_TAG_ATTRIBUTES)):
            attribute = LINK_TAG_ATTRIBUTES[tag.name]
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

    def _extract_ip_addresses(
        self, header_text: str | None, plain_text: str | None, html_text: str | None
    ) -> list[dict[str, Any]]:
        sources = {
            "header": header_text,
            "plain-text": plain_text,
            "html": html_text,
        }
        merged: dict[tuple[str, int | None, str | None], dict[str, Any]] = {}

        for source_name, text in sources.items():
            if not text:
                continue

            for match in self._find_ip_addresses(text):
                key = (match["ip"], match["port"], match["cidr"])
                existing = merged.get(key)

                if existing is None:
                    merged[key] = {
                        "source": [source_name],
                        "ip": match["ip"],
                        "version": match["version"],
                        "port": match["port"],
                        "cidr": match["cidr"],
                        "raw": match["matched"],
                    }
                elif source_name not in existing["source"]:
                    existing["source"].append(source_name)

        return list(merged.values())

    def _find_ip_addresses(self, text: str) -> list[dict[str, Any]]:
        """Scan `text` for IPv4/IPv6 literals, with optional ports or CIDR suffixes."""
        results: list[dict[str, Any]] = []
        index = 0
        length = len(text)

        while index < length:
            if text[index] not in IP_CANDIDATE_CHARS:
                index += 1
                continue

            start = index
            while index < length and text[index] in IP_CANDIDATE_CHARS:
                index += 1

            candidate = text[start:index]
            parsed = self._parse_ip_candidate(candidate)

            if parsed is not None:
                results.append(parsed)

        return results

    def _parse_ip_candidate(self, candidate: str) -> dict[str, Any] | None:
        """Parse a single whitespace-delimited candidate token into an IP match, if valid."""
        token = candidate.strip(".,;:()")

        # Bracketed IPv6 with optional port: [2001:db8::1] or [2001:db8::1]:80
        if token.startswith("["):
            parsed = self._parse_bracketed_ipv6(token)
            if parsed is not None:
                return parsed

        # CIDR / subnet notation: 10.0.0.1/24 or 2001:db8::/32
        if "/" in token:
            try:
                interface = ipaddress.ip_interface(token)
            except ValueError:
                pass
            else:
                return {
                    "ip": str(interface.ip),
                    "version": f"IPv{interface.version}",
                    "port": None,
                    "cidr": f"/{interface.network.prefixlen}",
                    "matched": token,
                }

        # IPv4 with a port: 192.168.1.1:8080
        if ":" in token:
            parsed = self._parse_ipv4_with_port(token)
            if parsed is not None:
                return parsed

        # Plain IPv4 or IPv6 address.
        try:
            ip_obj = ipaddress.ip_address(token)
        except ValueError:
            return None

        return {
            "ip": str(ip_obj),
            "version": f"IPv{ip_obj.version}",
            "port": None,
            "cidr": None,
            "matched": token,
        }

    def _parse_bracketed_ipv6(self, token: str) -> dict[str, Any] | None:
        end_bracket = token.find("]")
        if end_bracket == -1:
            return None

        ip_str = token[1:end_bracket]
        remainder = token[end_bracket + 1 :]

        try:
            ip_obj = ipaddress.ip_address(ip_str)
        except ValueError:
            return None

        if ip_obj.version != 6:
            return None

        port: int | None = None

        if remainder.startswith(":"):
            port_str = remainder[1:]
            if not (port_str.isdigit() and 0 <= int(port_str) <= 65535):
                return None
            port = int(port_str)
        elif remainder != "":
            return None

        matched = f"[{ip_str}]" if port is None else f"[{ip_str}]:{port}"

        return {
            "ip": str(ip_obj),
            "version": "IPv6",
            "port": port,
            "cidr": None,
            "matched": matched,
        }

    def _parse_ipv4_with_port(self, token: str) -> dict[str, Any] | None:
        ip_str, _, port_str = token.rpartition(":")
        if not ip_str or not port_str.isdigit():
            return None

        port = int(port_str)
        if not 0 <= port <= 65535:
            return None

        try:
            ip_obj = ipaddress.ip_address(ip_str)
        except ValueError:
            return None

        if ip_obj.version != 4:
            return None

        return {
            "ip": str(ip_obj),
            "version": "IPv4",
            "port": port,
            "cidr": None,
            "matched": token,
        }
