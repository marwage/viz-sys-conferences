.PHONY: run test stats lint fmt notebook

run:
	uv run python -m viz_sys_conferences --output data/

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
