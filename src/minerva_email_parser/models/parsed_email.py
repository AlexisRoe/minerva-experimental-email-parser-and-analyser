from __future__ import annotations

from pydantic import BaseModel, Field


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
    not embedded here — see `minerva_email_parser.service.file_storage`.
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
