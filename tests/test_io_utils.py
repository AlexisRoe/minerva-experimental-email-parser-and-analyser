from __future__ import annotations

from pathlib import Path

from minerva_email_parser.io_utils import discover_assets, open_asset_stream

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"


def test_discover_assets_finds_eml_files() -> None:
    assets = discover_assets(ASSETS_DIR)
    assert [asset.name for asset in assets] == ["base-extended.eml", "base.eml"]


def test_open_asset_stream_yields_readable_binary_stream() -> None:
    asset_path = ASSETS_DIR / "base.eml"
    with open_asset_stream(asset_path) as stream:
        data = stream.read()
    assert isinstance(data, bytes)
    assert data == asset_path.read_bytes()
