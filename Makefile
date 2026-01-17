.PHONY: start dev worker temporal-docker stop tunnel test-prod test test-ruby test-pinterest lint install format models run typecheck types types-publish

# =============================================================================
# Setup
# =============================================================================

install:
	uv sync --all-extras

# =============================================================================
# Development
# =============================================================================

# Start Temporal + Worker (single command, recommended)
start:
	./start.sh

# Alternative: separate terminals (useful for debugging)
dev:
	@echo "Starting Temporal dev server..."
	@echo "  UI: http://localhost:8080"
	@echo ""
	@echo "In another terminal, run: make worker"
	@echo ""
	temporal server start-dev --ui-port 8080

worker:
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	PYTHONUNBUFFERED=1 uv run python -m app.temporal.worker

# =============================================================================
# Docker-based (for production-like setup)
# =============================================================================

temporal-docker:
	docker compose up temporal -d
	@echo "Temporal UI: http://localhost:8233"

stop:
	docker compose down

# =============================================================================
# Production
# =============================================================================

# SSH tunnel to access Temporal UI on production server
# Usage: make tunnel HOST=your-server-ip
# Then open http://localhost:8080
tunnel:
ifndef HOST
	$(error HOST is required. Usage: make tunnel HOST=your-server-ip)
endif
	@echo "Opening SSH tunnel to $(HOST)..."
	@echo "Temporal UI will be available at: http://localhost:8080"
	@echo "Press Ctrl+C to close the tunnel"
	@echo ""
	ssh -L 8080:localhost:8080 root@$(HOST)

# Test production connection
test-prod:
	uv run python scripts/test_connection.py

# =============================================================================
# Testing
# =============================================================================

# Run unit tests (no Temporal needed, mocked)
test:
	uv run pytest -v

# Run manual tests (requires Temporal + Worker running)
test-manual:
	uv run pytest -m manual -v -s

# Run specific workflow test
test-ruby:
	uv run pytest -m manual tests/temporal/manual/test_ruby.py::test_ruby_basic -v -s

test-pinterest:
	uv run pytest -m manual tests/temporal/manual/test_slideshows_pinterest.py::test_pinterest_basic -v -s

# Run all tests (unit + manual)
test-all:
	uv run pytest -m "" -v

# =============================================================================
# Development
# =============================================================================

# List models
models:
	uv run python -c "from app.core.ai_models import model_registry; [print(f'{m.id}: {m.name}') for m in model_registry.list_all()]"

# Run a sample workflow (HelloWorld)
run:
	uv run python -c "\
import asyncio; \
from app.temporal.client import execute_workflow; \
from app.temporal.workflows import HelloWorldWorkflow, HelloWorldInput; \
print(asyncio.run(execute_workflow( \
    HelloWorldWorkflow.run, \
    HelloWorldInput(name='World'), \
)))"

# Lint
lint:
	uv run ruff check .

# Format
format:
	uv run ruff format .

# Type check
typecheck:
	uv run mypy app

# =============================================================================
# TypeScript Types Generation
# =============================================================================

# Generate TypeScript types and workflow registry
types:
	uv run python -m scripts.generate_types

# Generate with version bump and publish to NPM
types-publish:
	uv run python -m scripts.generate_types --bump patch
	cd generated && npm publish --access public
