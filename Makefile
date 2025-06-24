format:
	uv run ruff format src

lint:
	uv run ruff check src

type:
	uv run mypy --install-types --non-interactive src

test:
	uv run pytest -v -s --cov=src tests

publish:
	uv build --wheel
	uv publish

all: format lint type test

.PHONY: format lint test publish
