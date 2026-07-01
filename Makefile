.PHONY: lint fix typecheck

lint:
	uv run ruff check .
	uv run ruff format --check .

fix:
	uv run ruff check --fix .
	uv run ruff format .

typecheck:
	uv run mypy yt_music/
