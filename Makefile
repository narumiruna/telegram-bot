lint:
	uv run ruff check src

type:
	uv run mypy --install-types --non-interactive src

test:
	uv run pytest -v -s --cov=src tests

cover:
	uv run pytest -v -s --cov=src --cov-report=xml tests

publish:
	uv build --wheel
	uv publish

.PHONY: lint test publish
