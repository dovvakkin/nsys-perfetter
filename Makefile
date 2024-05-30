format:
	black .
	isort .

lint:
	ruff check .

docker-build:
	docker build nsys-perfetter .

docker-run:
	docker run -p 8501:8501 nsys-perfetter
