# Standard targets for a local Python script/tool project.
# Everything routes through `uv` so contributors don't need a manually
# managed virtualenv.

.PHONY: install run start test lint format check

install:
	uv sync

run:
	uv run python -m minerva_email_parser

start: run

test:
	uv run pytest

lint:
	uv run ruff check .
	uv run ruff format --check .

format:
	uv run ruff check --fix .
	uv run ruff format .

check: test lint
