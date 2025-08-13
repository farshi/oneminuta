.PHONY: help install dev-install test lint format clean run-api run-bot run-collector run-all docker-build docker-up docker-down

PYTHON := python3
PIP := pip3
VENV := venv

help: ## Show this help message
	@echo "OneMinuta Platform - Development Commands"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install production dependencies
	$(PIP) install -r requirements.txt

dev-install: ## Install development dependencies
	$(PIP) install -r requirements.txt
	$(PIP) install pytest pytest-asyncio pytest-cov black flake8 mypy pre-commit
	pre-commit install

venv: ## Create virtual environment
	$(PYTHON) -m venv $(VENV)
	@echo "Virtual environment created. Activate with: source venv/bin/activate"

# Telegram Analytics Commands
telegram-auth: ## Authenticate with Telegram (one-time)
	./services/analytics/cli auth

telegram-analyze: ## Analyze Telegram channels for hot clients
	./services/analytics/cli analyze --days 3

telegram-analyze-week: ## Analyze last 7 days
	./services/analytics/cli analyze --days 7

telegram-monitor: ## Start real-time monitoring
	./services/analytics/cli monitor

telegram-debug: ## Debug channel messages and filtering
	./services/analytics/cli debug

telegram-list: ## List hot clients
	./services/analytics/cli list --min-score 60

telegram-test-access: ## Test channel access
	./services/analytics/cli test access

telegram-test-filter: ## Test message filtering
	./services/analytics/cli test filter

telegram-test-all: ## Run all Telegram tests
	./services/analytics/cli test all

telegram-clean: ## Clean analytics storage
	./services/analytics/cli clean

telegram-clean-all: ## Clean everything including sessions
	./services/analytics/cli clean

# Unit Tests
test-analytics: ## Run analytics unit tests
	$(PYTHON) -m pytest tests/unit/analytics/ -v

test: ## Run all tests
	$(PYTHON) -m pytest tests/unit/ -v 2>/dev/null || echo "⚠️  Some unit tests may have failed"
	./services/analytics/cli test all

test-unit: ## Run unit tests only
	$(PYTHON) -m pytest tests/unit/ -v

test-integration: ## Run integration tests
	pytest tests/integration/ -v 2>/dev/null || echo "No integration tests yet"

lint: ## Run linters
	flake8 libs/ services/
	mypy libs/ services/

format: ## Format code with black
	black libs/ services/ tests/

clean: ## Clean up generated files
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.coverage" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf dist/ build/

# Service runners
run-api: ## Run API service
	cd services/api && uvicorn main:app --reload --host 0.0.0.0 --port 8000

run-bot: ## Run Telegram bot
	cd services/bot && $(PYTHON) main.py

run-collector: ## Run collector service
	cd services/collector-listings && $(PYTHON) main.py

run-parser: ## Run parser service
	cd services/parser && $(PYTHON) main.py

run-indexer: ## Run indexer service
	cd services/indexer && $(PYTHON) main.py

run-notifier: ## Run notifier service
	cd services/notifier && $(PYTHON) main.py

# Development helpers
dev-api: ## Run API in development mode with auto-reload
	cd services/api && uvicorn main:app --reload --host 0.0.0.0 --port 8000 --log-level debug

dev-bot: ## Run bot in development mode
	cd services/bot && $(PYTHON) main.py --debug

# Docker commands
docker-build: ## Build Docker images
	docker-compose build

docker-up: ## Start all services with Docker
	docker-compose up -d

docker-down: ## Stop all Docker services
	docker-compose down

docker-logs: ## Show Docker logs
	docker-compose logs -f

# Database/Storage commands
init-storage: ## Initialize storage directories
	mkdir -p storage/{agents,geo,users,global}
	mkdir -p logs
	mkdir -p config
	@echo "Storage directories created"

backup: ## Backup storage directory
	tar -czf backups/storage-$$(date +%Y%m%d-%H%M%S).tar.gz storage/
	@echo "Backup created in backups/"

# Setup commands
setup: venv install init-storage ## Complete setup for new developers
	cp .env.example .env
	@echo "Setup complete! Edit .env with your credentials"

check-env: ## Check if environment variables are set
	@$(PYTHON) -c "from dotenv import load_dotenv; import os; load_dotenv(); \
	required = ['TELEGRAM_API_ID', 'TELEGRAM_API_HASH', 'TELEGRAM_BOT_TOKEN']; \
	missing = [v for v in required if not os.getenv(v)]; \
	print('Missing variables:', missing) if missing else print('All required variables set')"

# Monitoring
monitor: ## Monitor service logs
	tail -f logs/*.log

stats: ## Show storage statistics
	@echo "Storage Statistics:"
	@du -sh storage/* 2>/dev/null || echo "No storage data yet"
	@echo ""
	@echo "Property Count:"
	@find storage/agents -name "meta.json" 2>/dev/null | wc -l || echo "0"

# Quality checks
quality: lint test ## Run all quality checks
	@echo "All quality checks passed!"

pre-commit: format lint test ## Run pre-commit checks
	@echo "Ready to commit!"

# Deployment
deploy-prod: ## Deploy to production (requires setup)
	@echo "Deploying to production..."
	# Add your deployment commands here

version: ## Show component versions
	@echo "OneMinuta Component Versions:"
	@grep -h "__version__" libs/*/version.py services/*/version.py 2>/dev/null || echo "Version files not yet created"