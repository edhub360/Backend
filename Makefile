.PHONY: test test-unit test-integration test-cov test-watch lint format clean

# Install test dependencies
install-test:
	pip install -r requirements-test.txt

# Run all tests
test:
	pytest tests/ -v

# Run only unit tests
test-unit:
	pytest tests/unit/ -v -m unit

# Run only integration tests
test-integration:
	pytest tests/integration/ -v -m integration

# Run tests with coverage report
test-cov:
	pytest tests/ --cov=quiz --cov=login --cov=courses --cov-report=html --cov-report=term-missing
	@echo "Coverage report: htmlcov/index.html"

# Run tests in watch mode (auto-run on file changes)
test-watch:
	pytest-watch tests/ -v

# Run specific test file
test-file:
	pytest tests/$(FILE) -v

# Lint code
lint:
	flake8 quiz login courses flashcard
	black --check quiz login courses flashcard
	mypy quiz login --ignore-missing-imports

# Format code
format:
	black quiz login courses flashcard
	isort quiz login courses flashcard

# Clean up
clean:
	find . -type d -name __pycache__ -exec rm -r {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .mypy_cache htmlcov coverage.xml
