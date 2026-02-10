.PHONY: setup run test lint fmt clean

ARGS ?=

setup:
	python -m venv .venv
	.venv/bin/pip install -e ".[dev]" || .venv/bin/pip install -r requirements-dev.txt

run:
	python -m ics_toolkit $(ARGS)

test:
	python -m pytest tests/ -v --cov=ics_toolkit --cov-report=term-missing

lint:
	ruff check ics_toolkit/ tests/

fmt:
	ruff format ics_toolkit/ tests/

clean:
	rm -rf __pycache__ .pytest_cache .coverage .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
