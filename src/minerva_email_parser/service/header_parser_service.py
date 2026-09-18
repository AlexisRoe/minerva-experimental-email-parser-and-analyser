from __future__ import annotations

from dataclasses import dataclass
from email.headerregistry import HeaderRegistry

# Header names email.headerregistry parses as a mailbox-list (i.e. `.addresses`
# yields one entry per address) rather than a single mailbox.
ADDRESS_HEADER_NAMES = {
    "from",
    "to",
    "cc",
    "bcc",
    "reply-to",
    "sender",
    "resent-from",
    "resent-to",
    "resent-cc",
    "resent-bcc",
    "resent-sender",
}


@dataclass(frozen=True)
class ParsedAddress:
    """A single normalized email address parsed out of an address-type header."""

    display_name: str
    email: str
    username: str
    domain: str


class HeaderParserService:
    """Normalizes raw email headers into structured data.

    Currently handles address-type headers (From, To, Cc, ...), using
    `email.headerregistry` to do the actual RFC 5322 address parsing
    (quoted display names, multiple/grouped addresses, comments, etc.)
    instead of hand-rolled regex.
    """

    def __init__(self) -> None:
        self._registry = HeaderRegistry()

    def is_address_header(self, header_name: str) -> bool:
        """Whether `header_name` is a header type that holds one or more addresses.

        Args:
            header_name: The header's name, e.g. 'From' or 'X-Mailer'.

        Returns:
            `True` if the header is a recognized address-type header
            (From, To, Cc, Bcc, Reply-To, Sender, or their Resent- variants).
        """
        return header_name.strip().lower() in ADDRESS_HEADER_NAMES

    def parse_address_header(self, header_name: str, raw_value: str) -> list[ParsedAddress]:
        """Parse an address-type header's raw value into structured addresses.

        Args:
            header_name: The header's name, e.g. 'From' or 'To'.
            raw_value: The header's raw, unfolded value.

        Returns:
            One `ParsedAddress` per address found. Entries that don't
            actually contain an '@' (i.e. the value wasn't a real address,
            just text `email.headerregistry` couldn't make sense of) are
            skipped rather than raising.
        """
        if not raw_value:
            return []

        header = self._registry(header_name, raw_value)
        addresses = getattr(header, "addresses", ())

        return [
            ParsedAddress(
                display_name=address.display_name,
                email=address.addr_spec,
                username=address.username,
                domain=address.domain,
            )
            for address in addresses
            if address.domain
        ]
