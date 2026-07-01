.PHONY: lint fix

lint:
	uv run ruff check .

fix:
	uv run ruff check --fix .
	uv run ruff format .
