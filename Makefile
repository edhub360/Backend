.PHONY: test test-unit test-integration lint format clean \
        test-ai_chat test-courses test-flashcard test-quiz \
        test-study_planner test-Notes test-login test-all-modules


SERVICES = ai_chat courses flashcard quiz study_planner Notes login


# Install test dependencies
install-test:
	pip install -r requirements-test.txt


# ── Run all tests (no coverage) ──────────────────────────────────
test:
	pytest tests/ -v


# Run only unit tests
test-unit:
	pytest tests/unit/ -v -m unit


# Run only integration tests
test-integration:
	pytest tests/integration/ -v -m integration


# ── Per-module test targets ───────────────────────────────────────
test-ai_chat:
	pytest tests/unit/ai_chat/ \
		--cov=ai_chat \
		--cov-report=term-missing \
		--cov-report=html:htmlcov/ai_chat \
		-v


test-courses:
	pytest tests/unit/courses/ \
		--cov=courses \
		--cov-report=term-missing \
		--cov-report=html:htmlcov/courses \
		-v


test-flashcard:
	pytest tests/unit/flashcard/ \
		--cov=flashcard \
		--cov-report=term-missing \
		--cov-report=html:htmlcov/flashcard \
		-v


test-quiz:
	pytest tests/unit/quiz/ \
		--cov=quiz \
		--cov-report=term-missing \
		--cov-report=html:htmlcov/quiz \
		-v


test-study_planner:
	pytest tests/unit/study_planner/ \
		--cov=study_planner \
		--cov-report=term-missing \
		--cov-report=html:htmlcov/study_planner \
		-v


test-Notes:
	pytest tests/unit/Notes/ \
		--cov=Notes \
		--cov-report=term-missing \
		--cov-report=html:htmlcov/Notes \
		-v


test-login:
	pytest tests/unit/login/ \
		--cov=login \
		--cov-report=term-missing \
		--cov-report=html:htmlcov/login \
		--asyncio-mode=auto \
		-v


# ── Run all modules sequentially with per-module coverage ────────
test-all-modules:
	@for svc in $(SERVICES); do \
		echo "\n══════════ $$svc ══════════"; \
		pytest tests/unit/$$svc/ \
			--cov=$$svc \
			--cov-report=term-missing \
			--cov-report=xml:coverage_$$svc.xml \
			--asyncio-mode=auto \
			-v --tb=short || true; \
	done


# ── Combined coverage (all modules in one report) ────────────────
test-cov:
	pytest tests/unit/ \
		$(foreach svc,$(SERVICES),--cov=$(svc)) \
		--cov-report=html:htmlcov \
		--cov-report=term-missing \
		--asyncio-mode=auto
	@echo "Coverage report: htmlcov/index.html"


# ── Run specific test file: make test-file FILE=unit/quiz/test_quiz.py
test-file:
	pytest tests/$(FILE) -v


# ── Watch mode ───────────────────────────────────────────────────
test-watch:
	pytest-watch tests/ -v


# ── Lint / Format ────────────────────────────────────────────────
lint:
	flake8 $(SERVICES) \
		--count --select=E9,F63,F7,F82 --show-source --statistics
	black --check $(SERVICES)
	mypy $(SERVICES) --ignore-missing-imports


format:
	black $(SERVICES)
	isort $(SERVICES)


# ── Clean ────────────────────────────────────────────────────────
clean:
	find . -type d -name __pycache__ -exec rm -r {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .mypy_cache htmlcov coverage*.xml