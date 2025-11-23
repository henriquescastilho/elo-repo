.PHONY: dev test start install clean

install:
	pip install -r requirements.txt

dev:
	uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000

start:
	uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --workers 4

test:
	pytest

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

deploy:
	docker-compose -f docker-compose.prod.yaml up -d --build
