from __future__ import annotations


def upload_attachment(attachment_id: str, file_name: str, content: bytes) -> str:
    """Upload an attachment's raw bytes to file storage.

    Not implemented yet — wire this up to the target file-storage backend
    (e.g. S3, Azure Blob Storage) once one is chosen. Until then, use-cases
    should skip calling this and omit attachment bytes from their output.

    Args:
        attachment_id: Stable identifier for the attachment (e.g. its content-id).
        file_name: Original file name of the attachment.
        content: The attachment's raw bytes.

    Returns:
        The URL or storage key the attachment was uploaded to.

    Raises:
        NotImplementedError: Always, until a file-storage backend is wired up.
    """
    raise NotImplementedError("File storage upload is not implemented yet")
