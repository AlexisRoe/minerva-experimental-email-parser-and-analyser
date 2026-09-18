from __future__ import annotations

import uuid
from base64 import b64decode
from pathlib import Path
from typing import Any, BinaryIO

import mailparser

from minerva_email_parser.service.file_storage import (
    DEFAULT_CONTENT_TYPE,
    LocalFileStorage,
    build_object_key,
)

# --- Use-case metadata (read by the CLI to build the selection menu) ---
NAME = "base-parser"
DESCRIPTION = "Parse a raw .eml byte stream into headers, body, and attachment metadata."

PROJECT_ROOT = Path(__file__).resolve().parents[3]
ATTACHMENTS_BUCKET_DIR = PROJECT_ROOT / "storage" / "attachments"


def run(stream: BinaryIO) -> dict[str, Any]:
    """Parse a raw email byte stream into a JSON-serializable structure.

    Args:
        stream: A binary stream of the loaded `.eml` file's contents.

    Returns:
        A dict with `headers`, `body`, and `attachments` keys.
    """
    mail = mailparser.parse_from_bytes(stream.read())
    storage = LocalFileStorage(ATTACHMENTS_BUCKET_DIR)

    return {
        "headers": _extract_headers(mail),
        "body": _extract_body(mail),
        "attachments": [_extract_attachment(attachment, storage) for attachment in mail.attachments],
    }


def _extract_headers(mail: mailparser.MailParser) -> list[dict[str, str]]:
    return [{"key": key, "value": str(value)} for key, value in mail.headers.items()]


def _extract_body(mail: mailparser.MailParser) -> dict[str, str | None]:
    return {
        "plainText": "\n".join(mail.text_plain) or None,
        "html": "\n".join(mail.text_html) or None,
    }


def _extract_attachment(attachment: dict[str, Any], storage: LocalFileStorage) -> dict[str, Any]:
    payload: str | None = attachment.get("payload")
    is_binary: bool = attachment.get("binary", False)
    content_type: str | None = attachment.get("mail_content_type")
    size_in_bytes = _attachment_size(payload, is_binary)

    attachment_id: str | None = attachment.get("content-id") or None
    internal_id: str | None = None
    if not attachment_id:
        internal_id = str(uuid.uuid4())

    if payload is not None:
        content = b64decode(payload) if is_binary else payload.encode(attachment.get("charset") or "utf-8")
        key = build_object_key(attachment_id or internal_id, content_type or DEFAULT_CONTENT_TYPE)
        storage.put_object(key, content, content_type=content_type)

    result: dict[str, Any] = {
        "contentType": content_type,
        "sizeInBytes": size_in_bytes,
        "fileName": attachment.get("filename"),
        "contentDisposition": attachment.get("content-disposition"),
        "charset": attachment.get("charset"),
        "id": attachment_id,
        "binary": is_binary,
    }
    if internal_id is not None:
        result["internalId"] = internal_id
    return result


def _attachment_size(payload: str | None, is_binary: bool) -> int:
    if payload is None:
        return 0
    if is_binary:
        return len(b64decode(payload))
    return len(payload.encode("utf-8"))
