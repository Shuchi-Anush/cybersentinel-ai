install:
	pip install -r requirements.txt

feature-selection:
	python src/features/selector.py

preprocess:
	python src/features/preprocessor.py

train-binary:
	python src/training/binary_trainer.py

train-multiclass:
	python src/training/multiclass_trainer.py

evaluate:
	python src/models/evaluator.py

api:
	uvicorn src.api.main:app --host 0.0.0.0 --port 8000

dashboard:
	streamlit run src/dashboard/app.py

docker-build:
	docker build -t cybersentinel .

docker-run:
	docker run -p 8000:8000 cybersentinel

run:
	python scripts/demo_runner.py

clean:
	find . -type d -name "__pycache__" -exec rm -r {} +
	find . -name "*.pyc" -delete
	find . -name "*.tmp" -delete