install:
	pip install -r requirements.txt

train:
	python src/pipeline/pipeline_runner.py

test:
	pytest tests/

api:
	uvicorn src.api.main:app --host 0.0.0.0 --port 8000

dashboard:
	streamlit run src/dashboard/app.py

docker-build:
	docker build -t cybersentinel .

docker-run:
	docker run -p 8000:8000 cybersentinel