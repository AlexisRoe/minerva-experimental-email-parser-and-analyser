from __future__ import annotations

from pathlib import Path

from minerva_email_parser.service.file_storage import LocalFileStorage, build_object_key


def test_build_object_key_uses_extension_from_known_content_type() -> None:
    assert build_object_key("abc-123", "image/png") == "abc-123.png"


def test_build_object_key_falls_back_to_bin_for_unknown_content_type() -> None:
    assert build_object_key("abc-123", None) == "abc-123.bin"
    assert build_object_key("abc-123", "application/x-does-not-exist") == "abc-123.bin"


def test_put_and_get_object_round_trips_bytes(tmp_path: Path) -> None:
    storage = LocalFileStorage(tmp_path)

    result = storage.put_object("abc-123.png", b"raw-bytes", content_type="image/png")

    assert result.key == "abc-123.png"
    assert (tmp_path / "abc-123.png").read_bytes() == b"raw-bytes"
    assert storage.get_object("abc-123.png") == b"raw-bytes"


def test_put_object_creates_bucket_dir_if_missing(tmp_path: Path) -> None:
    bucket_dir = tmp_path / "nested" / "bucket"
    storage = LocalFileStorage(bucket_dir)

    storage.put_object("file.bin", b"data")

    assert (bucket_dir / "file.bin").exists()
