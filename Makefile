.PHONY: setup initdb samples sample-run run test lint types check live
PYTHON ?= python

setup:
	$(PYTHON) -m pip install -r requirements.txt -r requirements-dev.txt
	$(PYTHON) -m pre_commit install

initdb:
	$(PYTHON) -m scripts.init_db

samples:
	$(PYTHON) scripts/generate_synthetic_pdfs.py
	$(PYTHON) scripts/generate_edge_case_pdfs.py

sample-run:
	$(PYTHON) -m scripts.export_sample_run

run:
	$(PYTHON) -m streamlit run app.py

test:
	$(PYTHON) -m pytest -q -m "not live_llm"

lint:
	$(PYTHON) -m ruff check .
	$(PYTHON) -m ruff format --check .

types:
	$(PYTHON) -m mypy rfp_eval

check: lint types test

live:
	$(PYTHON) -m pytest -m live_llm
