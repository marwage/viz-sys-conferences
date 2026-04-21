.PHONY: test stats lint fmt notebook dblp-extract

test:
	uv run pytest

stats:
	uv run stats

dblp-extract:
	uv run dblp-extract --output data/

notebook:
	uv run jupyter lab --notebook-dir=notebooks

lint:
	uv run ruff check .

fmt:
	uv run ruff format .
