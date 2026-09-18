from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

ArtefactSource = Literal["plain-text", "html", "both"]


class Header(BaseModel):
    """A single raw email header, in the order mailparser encountered it."""

    key: str = Field(description="Header name, e.g. 'Subject' or 'Message-ID'.")
    value: str = Field(description="Header value, stringified as mailparser returned it.")


class Body(BaseModel):
    """The email's decoded text content."""

    plainText: str | None = Field(
        description="Concatenated `text/plain` parts, or `None` if the email has none."
    )
    html: str | None = Field(description="Concatenated `text/html` parts, or `None` if the email has none.")


class Attachment(BaseModel):
    """Metadata for one attachment. Its raw bytes are written to file storage,
    not embedded here — see `minerva_email_parser.service.file_storage_service`.
    """

    contentType: str | None = Field(
        description="MIME type reported for the attachment, e.g. 'image/png'. "
        "`None` if mailparser could not determine one."
    )
    sizeInBytes: int = Field(description="Size of the decoded attachment content, in bytes.")
    fileName: str | None = Field(description="Original file name of the attachment, if present.")
    contentDisposition: str | None = Field(
        description="Raw `Content-Disposition` header value, e.g. 'attachment; filename=\"icon.png\"'."
    )
    charset: str | None = Field(description="Character set of the attachment content, if applicable.")
    id: str | None = Field(
        description="The attachment's `Content-ID`, with surrounding angle brackets stripped by "
        "mailparser. `None` if the source email didn't set one — see `internalId`."
    )
    binary: bool = Field(description="Whether the attachment content is binary (base64-encoded).")
    internalId: str | None = Field(
        default=None,
        description="Generated UUID used as the file-storage key, present only when the "
        "attachment had no `id` to use instead.",
    )


class Defect(BaseModel):
    """A parsing problem mailparser/`email` flagged in one MIME part.

    Malformed input (bad boundaries, broken encodings, etc.) doesn't stop
    parsing — it's surfaced here instead so callers can decide whether to
    trust the rest of the result.
    """

    partContentType: str = Field(description="Content type of the MIME part the defect was found in.")
    type: str = Field(
        description="Name of the underlying `email.errors` defect class, e.g. 'CloseBoundaryNotFoundDefect'."
    )
    description: str = Field(description="Human-readable explanation of the defect.")


class PhoneNumberArtefact(BaseModel):
    """A phone number found in the email body."""

    source: ArtefactSource = Field(
        description="Where the number was found: the plain-text body, the HTML body, or both."
    )
    value: str = Field(description="The number, normalized to E.164 (e.g. '+15550192834').")
    isValid: bool = Field(
        description="Whether `phonenumbers` considers this a valid, dialable number "
        "(vs. merely a plausible-looking match)."
    )
    region: str | None = Field(
        description="ISO 3166-1 alpha-2 region code `phonenumbers` attributes the number to, "
        "or `None` if it couldn't determine one."
    )


class EmailAddressArtefact(BaseModel):
    """An email address found in the email body (as opposed to its headers)."""

    source: ArtefactSource = Field(
        description="Where the address was found: the plain-text body, the HTML body, or both."
    )
    value: str = Field(description="The address exactly as it appeared in the body.")
    isValid: bool = Field(
        description="Whether `email_validator` accepts this as a syntactically valid address "
        "(no deliverability/DNS check is performed)."
    )
    domain: str = Field(
        description="The part of the address after the '@', useful for spotting "
        "look-alike or mismatched sender domains during investigation."
    )


class LinkArtefact(BaseModel):
    """A URL or resource reference found in the email body."""

    source: ArtefactSource = Field(
        description="Where the link was found: the plain-text body, the HTML body, or both."
    )
    type: str = Field(
        description="The link's URI scheme (e.g. 'http', 'https', 'mailto', 'ftp', 'tel'), "
        "'relative' if it has none, or 'src' for non-hyperlink references such as <img src> "
        "or <script src> where there's no meaningful scheme to report separately."
    )
    visible: str | None = Field(
        description="The link's visible anchor text, only present for `<a href>` tags found in "
        "HTML. `None` for plain-text links and for non-anchor references like <img src>."
    )
    href: str = Field(description="The raw URL or resource reference, exactly as it appeared.")
    domain: str | None = Field(
        description="Host portion of the URL (e.g. 'example.com'), or `None` if it couldn't be "
        "determined (e.g. a relative path or a malformed URL)."
    )


class Artefacts(BaseModel):
    """Links, phone numbers, and email addresses extracted from the email body.

    Extraction only considers the plain-text body and the `<body>` of the
    HTML (falling back to the whole document for HTML fragments without a
    `<body>` tag) — not the raw headers or attachment content.
    """

    links: list[LinkArtefact] = Field(description="URLs and resource references found in the body.")
    phoneNumbers: list[PhoneNumberArtefact] = Field(description="Phone numbers found in the body.")
    emailAddresses: list[EmailAddressArtefact] = Field(description="Email addresses found in the body.")


class ParsedEmail(BaseModel):
    """The structured result returned by the `base-parser` use-case.

    Matches the JSON object printed to the console or written to
    `output/` by the CLI (`minerva_email_parser.main`).
    """

    headers: list[Header] = Field(description="All headers from the email, in their original order.")
    body: Body = Field(description="The email's decoded plain-text and HTML content.")
    attachments: list[Attachment] = Field(description="Metadata for every attachment found in the email.")
    defects: list[Defect] = Field(
        description="Parsing problems found while decoding the email's MIME parts. Empty for "
        "well-formed emails."
    )
    artefacts: Artefacts = Field(
        description="Links, phone numbers, and email addresses extracted from the body, for "
        "investigation (e.g. phishing indicators, contact harvesting)."
    )
