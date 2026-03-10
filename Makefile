install:
	pip install -r requirements.txt

train:
	python src/pipeline/pipeline_runner.py

test:
	pytest tests/

docker-build:
	docker build -t cybersentinel .

docker-run:
	docker run -p 8000:8000 cybersentinel