.PHONY: install run-api run-dashboard test lint scenario clean

install:
	python -m pip install -r requirements.txt

run-api:
	python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload

run-dashboard:
	streamlit run src/dashboard/app.py

test:
	python -m pytest tests/ --tb=short

lint:
	python -m ruff check src/ scripts/ tests/

scenario:
	python -m scripts.scenario_extractor
	python -m scripts.scenario_validator

clean:
	rm -rf __pycache__ .pytest_cache htmlcov .coverage
	find . -type d -name "__pycache__" -exec rm -rf {} +