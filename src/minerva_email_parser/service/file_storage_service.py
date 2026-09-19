from __future__ import annotations

import mimetypes
from dataclasses import dataclass
from pathlib import Path

DEFAULT_CONTENT_TYPE = "application/octet-stream"
FALLBACK_EXTENSION = ".bin"


@dataclass(frozen=True)
class PutObjectResult:
    """Mirrors the subset of boto3 S3Client.put_object()'s response we care about."""

    key: str
    bucket: str
    location: str


class LocalFileStorage:
    """Disk-backed stand-in for an S3-compatible object store.

    Exposes the same shape as boto3's S3 client (`put_object`/`get_object`) so
    a real S3 client can be swapped in later without changing call sites.
    """

    def __init__(self, bucket_dir: Path) -> None:
        self._bucket_dir = bucket_dir

    def put_object(self, key: str, body: bytes, content_type: str | None = None) -> PutObjectResult:
        """Store an object's bytes under `key`.

        Args:
            key: Object key (file name, including extension) to store the bytes under.
            body: Raw bytes to store.
            content_type: MIME type of the content. Kept for interface parity
                with S3's `put_object`; a real S3 client would set it as
                object metadata, local storage has no use for it.

        Returns:
            Metadata about the stored object.
        """
        del content_type
        self._bucket_dir.mkdir(parents=True, exist_ok=True)
        object_path = self._bucket_dir / key
        object_path.write_bytes(body)

        return PutObjectResult(key=key, bucket=str(self._bucket_dir), location=str(object_path))

    def get_object(self, key: str) -> bytes:
        """Read back an object's bytes by key.

        Args:
            key: Object key the bytes were stored under.

        Returns:
            The object's raw bytes.
        """
        return (self._bucket_dir / key).read_bytes()


def build_object_key(object_id: str, content_type: str | None) -> str:
    """Build a storage key from an object id and its content type.

    Args:
        object_id: Stable identifier used as the file's base name.
        content_type: The object's MIME type, or `None`/empty if unknown.

    Returns:
        A file name like `<object_id><extension>`, falling back to a generic
        binary extension when the content type is missing or unrecognized.
    """
    extension = mimetypes.guess_extension(content_type or "") or FALLBACK_EXTENSION
    return f"{object_id}{extension}"
