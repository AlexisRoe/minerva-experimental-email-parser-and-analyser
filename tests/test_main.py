from __future__ import annotations

from pathlib import Path


def test_project_dirs_point_at_expected_locations() -> None:
    from minerva_email_parser.main import ASSETS_DIR, USE_CASE_DIR

    repo_root = Path(__file__).resolve().parent.parent
    assert (repo_root / "assets") == ASSETS_DIR
    assert (repo_root / "src" / "minerva_email_parser" / "use-case") == USE_CASE_DIR


def test_select_returns_the_chosen_choices_value(monkeypatch: object) -> None:
    import questionary

    from minerva_email_parser.main import Choice, _select

    class _FakeQuestion:
        def ask(self) -> str:
            return "picked"

    monkeypatch.setattr(  # type: ignore[attr-defined]
        questionary, "select", lambda *_args, **_kwargs: _FakeQuestion()
    )

    result = _select("Pick one:", [Choice(title="a", value="picked")])

    assert result == "picked"
