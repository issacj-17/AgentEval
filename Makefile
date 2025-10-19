.PHONY: help install install-dev install-hooks format lint type-check security-check test test-unit test-integration test-e2e test-all clean

help:  ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## Install production dependencies
	pip install -e .

install-dev:  ## Install development dependencies
	pip install -e ".[dev]"

install-hooks:  ## Install pre-commit hooks
	pre-commit install
	@echo "Pre-commit hooks installed successfully!"

format:  ## Format code and markdown with ruff and mdformat
	ruff format src tests
	ruff check --fix src tests
	mdformat *.md docs/ req-docs/ architecture/

lint:  ## Run linting checks
	ruff check src tests
	ruff format --check src tests
	mdformat --check *.md docs/ req-docs/ architecture/

type-check:  ## Run type checking with mypy
	mypy src

test-unit:  ## Run unit tests
	pytest tests/unit -v

test-integration:  ## Run integration tests
	pytest tests/integration -v

test-e2e:  ## Run end-to-end tests
	pytest tests/e2e -v

test:  ## Run all tests with coverage
	pytest tests -v --cov=agenteval --cov-report=html --cov-report=term

test-all: lint type-check security-check test  ## Run all checks and tests

clean:  ## Clean generated files
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	rm -rf build dist htmlcov .coverage
