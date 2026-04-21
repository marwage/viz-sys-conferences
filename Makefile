.PHONY: run test stats lint fmt

run:
	uv run python -m viz_sys_conferences --output data/

test:
	uv run pytest

stats:
	uv run stats

lint:
	uv run ruff check .

fmt:
	uv run ruff format .
