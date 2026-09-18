from __future__ import annotations

import uuid
from base64 import b64decode
from typing import Any, BinaryIO

import mailparser

# --- Use-case metadata (read by the CLI to build the selection menu) ---
NAME = "base-parser"
DESCRIPTION = "Parse a raw .eml byte stream into headers, body, and attachment metadata."


def run(stream: BinaryIO) -> dict[str, Any]:
    """Parse a raw email byte stream into a JSON-serializable structure.

    Args:
        stream: A binary stream of the loaded `.eml` file's contents.

    Returns:
        A dict with `headers`, `body`, and `attachments` keys.
    """
    mail = mailparser.parse_from_bytes(stream.read())

    return {
        "headers": _extract_headers(mail),
        "body": _extract_body(mail),
        "attachments": [_extract_attachment(attachment) for attachment in mail.attachments],
    }


def _extract_headers(mail: mailparser.MailParser) -> list[dict[str, str]]:
    return [{"key": key, "value": str(value)} for key, value in mail.headers.items()]


def _extract_body(mail: mailparser.MailParser) -> dict[str, str | None]:
    return {
        "plainText": "\n".join(mail.text_plain) or None,
        "html": "\n".join(mail.text_html) or None,
    }


def _extract_attachment(attachment: dict[str, Any]) -> dict[str, Any]:
    payload: str | None = attachment.get("payload")
    is_binary: bool = attachment.get("binary", False)
    size_in_bytes = _attachment_size(payload, is_binary)
    attachment_id = attachment.get("content-id") or str(uuid.uuid4())

    # Attachment bytes are skipped here — they get pushed to file storage
    # instead of being embedded in the parsed output. Once a backend is
    # wired up in file_storage.py, upload here, e.g.:
    # content = b64decode(payload) if is_binary else payload.encode(attachment.get("charset") or "utf-8")
    # minerva_email_parser.file_storage.upload_attachment(attachment_id, attachment["filename"], content)

    return {
        "contentType": attachment.get("mail_content_type"),
        "sizeInBytes": size_in_bytes,
        "fileName": attachment.get("filename"),
        "contentDisposition": attachment.get("content-disposition"),
        "charset": attachment.get("charset"),
        "id": attachment_id,
        "binary": is_binary,
    }


def _attachment_size(payload: str | None, is_binary: bool) -> int:
    if payload is None:
        return 0
    if is_binary:
        return len(b64decode(payload))
    return len(payload.encode("utf-8"))
