.PHONY: run embed test stats lint fmt notebook

run:
	uv run extract --output data/

embed:
	uv run embed

test:
	uv run pytest

stats:
	uv run stats

notebook:
	uv run jupyter lab --notebook-dir=notebooks

lint:
	uv run ruff check .

fmt:
	uv run ruff format .
