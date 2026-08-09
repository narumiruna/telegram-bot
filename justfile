
[default]
all: format check ty test

format:
    uv run ruff format src tests
check:
    uv run ruff check src tests

ty:
    uv run ty check src tests
test:
    uv run pytest -v -s --cov=src tests
