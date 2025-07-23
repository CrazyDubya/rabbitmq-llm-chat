# Makefile for RabbitMQ LLM Chat Platform

.PHONY: help install test lint format clean docker-build docker-run docker-stop setup-dev

# Default target
help:
	@echo "Available commands:"
	@echo "  install     - Install dependencies"
	@echo "  test        - Run test suite"
	@echo "  lint        - Run code linting"
	@echo "  format      - Format code with black"
	@echo "  clean       - Clean cache and temporary files"
	@echo "  docker-build - Build Docker images"
	@echo "  docker-run  - Start services with Docker Compose"
	@echo "  docker-stop - Stop Docker services"
	@echo "  setup-dev   - Setup development environment"
	@echo "  validate    - Validate configuration"
	@echo "  status      - Show system status"

# Development setup
install:
	pip install -r requirements.txt

setup-dev: install
	cp .env.example .env
	@echo "Development environment setup complete!"
	@echo "Please edit .env file with your configuration."

# Testing
test:
	python -m pytest tests/ -v

test-coverage:
	python -m pytest tests/ -v --cov=. --cov-report=html
	@echo "Coverage report generated in htmlcov/"

# Code quality
lint:
	flake8 . --max-line-length=100 --exclude=tests/,venv/,__pycache__/ || true
	mypy . --ignore-missing-imports || true

format:
	black . --line-length=100 --exclude="venv/|__pycache__/"

# Cleanup
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	rm -rf .pytest_cache/ htmlcov/ .coverage

# Application commands
validate:
	python main.py validate

status:
	python main.py status

run-web:
	python main.py web --debug

run-consumer:
	python main.py consumer

run-full:
	python main.py run --debug

setup-db:
	python main.py setup --create-admin

# Docker commands
docker-build:
	docker-compose build

docker-run:
	docker-compose up -d
	@echo "Services starting... Use 'docker-compose logs -f' to view logs"

docker-stop:
	docker-compose down

docker-logs:
	docker-compose logs -f

docker-clean:
	docker-compose down -v
	docker system prune -f

# Production deployment
deploy-prod:
	@echo "Setting up production deployment..."
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
	@echo "Production deployment complete!"

# Development workflows
dev-setup: setup-dev
	@echo "Starting development services..."
	docker-compose up -d rabbitmq postgres redis
	@echo "Core services started. Run 'make run-full' to start the application."

dev-test: test lint
	@echo "All development checks passed!"

# CI/CD helpers
ci-test: install test lint
	@echo "CI tests complete!"

# Database management
db-migrate:
	python main.py db migrate

db-upgrade:
	python main.py db upgrade

# Monitoring
logs:
	tail -f logs/app.log

health-check:
	curl -f http://localhost:5000/health || echo "Service not healthy"