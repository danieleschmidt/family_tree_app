# Family Tree App - Development Makefile
# Provides convenient commands for common development tasks

.PHONY: help install dev test lint format clean migrate collectstatic docker-up docker-down

# Default target
help:
	@echo "Family Tree App Development Commands"
	@echo "===================================="
	@echo ""
	@echo "Setup:"
	@echo "  install         Install all dependencies"
	@echo "  migrate         Run database migrations"
	@echo "  createsuperuser Create Django superuser"
	@echo ""
	@echo "Development:"
	@echo "  dev             Start development server"
	@echo "  shell           Open Django shell"
	@echo "  dbshell         Open database shell"
	@echo ""
	@echo "Testing:"
	@echo "  test            Run all tests"
	@echo "  test-unit       Run unit tests only"
	@echo "  test-integration Run integration tests only"
	@echo "  test-performance Run performance tests only"
	@echo "  test-coverage   Run tests with coverage report"
	@echo ""
	@echo "Code Quality:"
	@echo "  lint            Run linting (flake8)"
	@echo "  format          Format code (black + isort)"
	@echo "  typecheck       Run type checking (mypy)"
	@echo "  security        Run security checks (bandit)"
	@echo "  quality         Run all quality checks"
	@echo ""
	@echo "Docker:"
	@echo "  docker-up       Start Docker services"
	@echo "  docker-down     Stop Docker services"
	@echo "  docker-build    Build Docker images"
	@echo ""
	@echo "Maintenance:"
	@echo "  clean           Clean temporary files"
	@echo "  collectstatic   Collect static files"
	@echo "  backup          Create database backup"
	@echo "  restore         Restore from backup"

# Setup commands
install:
	@echo "Installing dependencies..."
	poetry install
	pip install -r extra_requirements.txt
	@echo "Setting up pre-commit hooks..."
	pre-commit install
	@echo "Installation complete!"

migrate:
	@echo "Running database migrations..."
	python source/manage.py migrate

createsuperuser:
	@echo "Creating Django superuser..."
	python source/manage.py createsuperuser

# Development commands
dev:
	@echo "Starting development server..."
	python source/manage.py runserver

shell:
	@echo "Opening Django shell..."
	python source/manage.py shell

dbshell:
	@echo "Opening database shell..."
	python source/manage.py dbshell

# Testing commands
test:
	@echo "Running all tests..."
	pytest -v

test-unit:
	@echo "Running unit tests..."
	pytest tests/unit/ -v

test-integration:
	@echo "Running integration tests..."
	pytest tests/integration/ -v

test-performance:
	@echo "Running performance tests..."
	pytest tests/performance/ -v -m slow

test-coverage:
	@echo "Running tests with coverage..."
	pytest --cov=source --cov-report=html --cov-report=term-missing

# Code quality commands
lint:
	@echo "Running linting checks..."
	flake8 source/ tests/

format:
	@echo "Formatting code..."
	black source/ tests/
	isort source/ tests/

typecheck:
	@echo "Running type checking..."
	mypy source/

security:
	@echo "Running security checks..."
	bandit -r source/ -f json

quality: lint typecheck security
	@echo "All quality checks complete!"

# Docker commands
docker-up:
	@echo "Starting Docker services..."
	docker-compose up -d

docker-down:
	@echo "Stopping Docker services..."
	docker-compose down

docker-build:
	@echo "Building Docker images..."
	docker-compose build

# Maintenance commands
clean:
	@echo "Cleaning temporary files..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type f -name "*.log" -delete
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .mypy_cache/

collectstatic:
	@echo "Collecting static files..."
	python source/manage.py collectstatic --noinput

backup:
	@echo "Creating database backup..."
	mkdir -p backups
	python source/manage.py dumpdata --natural-foreign --natural-primary > backups/backup_$(shell date +%Y%m%d_%H%M%S).json

restore:
	@echo "Restoring from backup..."
	@read -p "Enter backup file path: " backup_file; \
	python source/manage.py loaddata $$backup_file

# Development environment setup
setup-dev: install migrate
	@echo "Development environment setup complete!"
	@echo "Run 'make dev' to start the development server"

# Production deployment preparation
setup-prod: install migrate collectstatic
	@echo "Production setup complete!"

# Check system requirements
check:
	@echo "Checking system requirements..."
	python source/manage.py check
	python source/manage.py check --deploy

# Reset development database
reset-db:
	@echo "Resetting development database..."
	rm -f source/db.sqlite3
	python source/manage.py migrate
	@echo "Database reset complete. Run 'make createsuperuser' to create admin user."

# Load sample data
load-sample-data:
	@echo "Loading sample data..."
	python source/manage.py loaddata fixtures/sample_data.json

# Generate requirements.txt from poetry
export-requirements:
	@echo "Generating requirements.txt..."
	poetry export -f requirements.txt --output requirements.txt
	poetry export -f requirements.txt --dev --output requirements-dev.txt

# Documentation generation
docs:
	@echo "Generating documentation..."
	cd docs && mkdocs build

docs-serve:
	@echo "Serving documentation..."
	cd docs && mkdocs serve

# Performance monitoring
monitor:
	@echo "Starting performance monitoring..."
	python source/manage.py runserver --settings=app.conf.development.settings

# Quick commands for common workflows
quick-test: format lint test-unit
	@echo "Quick test cycle complete!"

quick-deploy: quality test setup-prod
	@echo "Ready for deployment!"

# Database management
dump-db:
	@echo "Dumping database..."
	python source/manage.py dumpdata --indent=2 > database_dump.json

load-db:
	@echo "Loading database..."
	python source/manage.py loaddata database_dump.json

# Translation management
makemessages:
	@echo "Creating translation messages..."
	cd source && python manage.py makemessages -a

compilemessages:
	@echo "Compiling translation messages..."
	cd source && python manage.py compilemessages

# Cache management
clear-cache:
	@echo "Clearing cache..."
	python source/manage.py shell -c "from django.core.cache import cache; cache.clear()"

# Log analysis
logs:
	@echo "Showing recent logs..."
	tail -f logs/family_tree.log

# Help for specific commands
help-test:
	@echo "Testing Commands Help"
	@echo "===================="
	@echo "test           - Run all tests with pytest"
	@echo "test-unit      - Run only unit tests"
	@echo "test-integration - Run only integration tests"
	@echo "test-performance - Run performance/load tests"
	@echo "test-coverage  - Run tests with coverage reporting"
	@echo ""
	@echo "Examples:"
	@echo "  make test                    # Run all tests"
	@echo "  make test-unit              # Quick unit tests only"
	@echo "  pytest tests/unit/test_models.py  # Specific test file"