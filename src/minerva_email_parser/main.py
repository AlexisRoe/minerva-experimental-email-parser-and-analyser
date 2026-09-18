from __future__ import annotations

import json
import sys
from pathlib import Path

import questionary
from questionary import Choice

from minerva_email_parser.io_utils import discover_assets, open_asset_stream, write_json_output
from minerva_email_parser.use_case_loader import UseCase, discover_use_cases

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
PACKAGE_DIR = Path(__file__).resolve().parent
USE_CASE_DIR = PACKAGE_DIR / "use-case"
ASSETS_DIR = PROJECT_ROOT / "assets"
OUTPUT_DIR = PROJECT_ROOT / "output"


def _select(message: str, choices: list[Choice]) -> object:
    """Show an arrow-key selection menu and return the chosen value.

    Args:
        message: Prompt shown above the menu.
        choices: Selectable options.

    Returns:
        The `value` of the chosen `Choice`, or `None` if the user cancelled
        (e.g. Ctrl-C).
    """
    return questionary.select(message, choices=choices).ask()


def main() -> None:
    """Entry point: let the user pick a use-case and an asset to run it against."""
    print("📬 Minerva Email Parser\n")

    use_cases = discover_use_cases(USE_CASE_DIR)
    if not use_cases:
        print(f"⚠️  No use-cases found in {USE_CASE_DIR}")
        sys.exit(1)

    use_case: UseCase | None = _select(
        "🧩 Which use-case do you want to run?",
        [Choice(title=uc.name, value=uc) for uc in use_cases],
    )
    if use_case is None:
        print("👋 Cancelled.")
        return
    print(f"   └─ {use_case.description}")

    assets = discover_assets(ASSETS_DIR)
    if not assets:
        print(f"⚠️  No asset files found in {ASSETS_DIR}")
        sys.exit(1)

    asset_path: Path | None = _select(
        "📄 Which asset do you want to run it against?",
        [Choice(title=asset.name, value=asset) for asset in assets],
    )
    if asset_path is None:
        print("👋 Cancelled.")
        return

    print(f"\n🚀 Running '{use_case.name}' against '{asset_path.name}'...\n")
    with open_asset_stream(asset_path) as stream:
        result = use_case.run(stream)

    destination = _select(
        "💾 What should happen with the result?",
        [
            Choice(title="🖥️  Print to console", value="console"),
            Choice(title="📁 Write to file", value="file"),
        ],
    )
    if destination is None:
        print("👋 Cancelled.")
        return

    if destination == "console":
        print(json.dumps(result, indent=2))
    else:
        file_name = f"{use_case.name}_{asset_path.stem}.json"
        output_path = write_json_output(OUTPUT_DIR, file_name, result)
        print(f"📁 Written to {output_path}")

    print("\n✅ Done.")


if __name__ == "__main__":
    main()
