from __future__ import annotations

from minerva_email_parser.main import main


def test_main_runs(capsys: object) -> None:
    main()
    captured = capsys.readouterr()  # type: ignore[attr-defined]
    assert "Hello from minerva-email-parser!" in captured.out
