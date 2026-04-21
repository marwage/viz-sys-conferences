.PHONY: run test stats

run:
	uv run python -m viz_sys_conferences --output data/

test:
	uv run pytest

stats:
	uv run python scripts/stats.py
