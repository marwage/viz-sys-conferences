.PHONY: run test stats lint fmt

run:
	uv run python -m viz_sys_conferences --output data/

test:
	uv run pytest

stats:
	uv run python scripts/stats.py

lint:
	uv run ruff check .

fmt:
	uv run ruff format .
