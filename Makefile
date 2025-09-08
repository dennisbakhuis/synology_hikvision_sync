# Makefile for Synology Hikvision Sync
# Author: Dennis Bakhuis
# Date: 2025-09-06

.PHONY: run test test-unit test-integration test-edge test-loggers test-extraction test-coverage clean install-dev help

# Default target
all: help

# Run the Python script
run:
	@echo "🚀 Running Hikvision sync script..."
	@uv run python src/sync_hikvision_cameras.py

# Run all tests
test: test-unit test-integration test-edge test-loggers test-extraction test-system test-coverage-report
	@echo "✅ All tests completed successfully with coverage report"

# Run unit tests
test-unit:
	@echo "🧪 Running unit tests..."
	@uv run pytest tests/test_parse_camera_translation.py tests/test_discover_cameras.py tests/test_log_message.py tests/test_hikvision_sync_init.py tests/test_hikvision_sync_logging.py -v

# Run integration tests
test-integration:
	@echo "🔗 Running integration tests..."
	@uv run pytest tests/test_hikvision_sync_integration.py -v

# Run edge case tests
test-edge:
	@echo "🔍 Running edge case tests..."
	@uv run pytest tests/test_hikvision_sync_retention_policy.py -v

# Run logger tests
test-loggers:
	@echo "📝 Running logger tests..."
	@uv run pytest tests/test_log_message.py tests/test_hikvision_sync_logging.py -v

# Run extraction tests
test-extraction:
	@echo "📤 Running extraction tests..."
	@uv run pytest tests/test_hikvision_sync_process_camera.py tests/test_hikvision_sync_process_media.py -v

# Run system tests
test-system:
	@echo "🏗️ Running system tests..."
	@uv run pytest tests/test_hikvision_sync_locking.py tests/test_hikvision_sync_directories.py tests/test_hikvision_sync_summary_report.py tests/test_hikvision_sync_run.py tests/test_hikvision_scheduler.py -v

# Run tests with coverage report
test-coverage:
	@echo "📊 Running tests with coverage..."
	@uv run pytest --cov=src --cov-report=html --cov-report=term-missing tests/test_*.py

# Generate coverage report (used by main test target)
test-coverage-report:
	@echo ""
	@echo "📊 Generating coverage report..."
	@uv run pytest --cov=src --cov-report=html --cov-report=term-missing tests/test_*.py --quiet
	@echo ""
	@echo "📄 HTML coverage report generated in htmlcov/index.html"

# Run specific test file
test-file:
	@echo "🎯 Running specific test file: $(FILE)"
	@uv run pytest $(FILE) -v

# Run tests matching a pattern
test-pattern:
	@echo "🔍 Running tests matching pattern: $(PATTERN)"
	@uv run pytest -k "$(PATTERN)" -v

# Check code syntax and style
lint:
	@echo "🔍 Checking code syntax and style..."
	@uv run python -m py_compile src/sync_hikvision_cameras.py && echo "  ✓ src/sync_hikvision_cameras.py syntax OK"
	@uv run pytest --collect-only tests/ >/dev/null && echo "  ✓ All test files syntax OK"

# Docker operations
docker-build:
	@echo "🐳 Building Docker image for x86_64 (for compatibility testing)..."
	@if command -v docker buildx >/dev/null 2>&1; then \
		docker buildx build --platform linux/amd64 -t synology_hikvision_sync .; \
	else \
		echo "  ⚠️  docker buildx not available, falling back to regular build"; \
		docker build -t synology_hikvision_sync .; \
	fi
	@echo "  ✓ Docker image built successfully"

docker-build-local:
	@echo "🐳 Building Docker image for local architecture..."
	@docker build -t synology_hikvision_sync .
	@echo "  ✓ Docker image built successfully for local architecture"

docker-build-multi:
	@echo "🐳 Building Docker image for multiple architectures..."
	@docker buildx build --platform linux/amd64,linux/arm64 -t synology_hikvision_sync .
	@echo "  ✓ Docker image built successfully for multiple architectures"

docker-run:
	@echo "🐳 Running Docker container (example)..."
	@echo "  Edit the volume mounts in this command for your setup:"
	@echo "  docker run --rm -v /path/to/input:/input:ro -v /path/to/output:/output synology_hikvision_sync"

docker-test:
	@echo "🧪 Testing Docker image..."
	@docker run --rm synology_hikvision_sync python -c "import sys; sys.path.insert(0, '/app/src'); import sync_hikvision_cameras; print('✓ Docker image works correctly')"

docker-build-and-test: docker-build docker-test
	@echo "🎉 Docker image built and tested successfully!"

# Install development dependencies
install-dev:
	@echo "📦 Installing development dependencies..."
	@uv sync --group dev
	@echo "  ✓ Development dependencies installed"

# Clean up temporary files and caches
clean:
	@echo "🧹 Cleaning up..."
	@rm -rf /tmp/hikvision_cache
	@rm -f /tmp/sync_hikvision_cameras.lock
	@rm -rf __pycache__
	@rm -rf src/__pycache__
	@rm -rf tests/__pycache__
	@rm -rf .pytest_cache
	@rm -rf htmlcov
	@rm -rf .coverage
	@rm -f .coverage.*
	@find . -name "*.pyc" -delete
	@find . -name "*.pyo" -delete
	@echo "  ✓ Cleanup completed"

# Run tests in watch mode (requires pytest-watch)
test-watch:
	@echo "👀 Running tests in watch mode..."
	@uv run pytest-watch

# Show usage information
help:
	@echo "Synology Hikvision Sync - Available Commands:"
	@echo ""
	@echo "🏃 Execution:"
	@echo "  make run              - Run the Hikvision sync script"
	@echo ""
	@echo "🧪 Testing:"
	@echo "  make test             - Run all tests with coverage report"
	@echo "  make test-unit        - Run unit tests only"
	@echo "  make test-integration - Run integration tests only"
	@echo "  make test-edge        - Run edge case tests only"
	@echo "  make test-loggers     - Run logger tests only"
	@echo "  make test-extraction  - Run extraction tests only"
	@echo "  make test-coverage    - Run tests with detailed coverage report"
	@echo "  make test-file FILE=path/to/test.py - Run specific test file"
	@echo "  make test-pattern PATTERN=test_name - Run tests matching pattern"
	@echo "  make test-watch       - Run tests in watch mode"
	@echo ""
	@echo "🔧 Development:"
	@echo "  make lint             - Check syntax and style"
	@echo "  make install-dev      - Install development dependencies"
	@echo "  make clean            - Clean up temporary files and caches"
	@echo ""
	@echo "🐳 Docker:"
	@echo "  make docker-build         - Build Docker image for x86_64 (compatibility testing)"
	@echo "  make docker-build-local   - Build Docker image for local architecture"
	@echo "  make docker-build-multi   - Build Docker image for multiple architectures"
	@echo "  make docker-test          - Test Docker image functionality"
	@echo "  make docker-build-and-test- Build and test Docker image in one step"
	@echo "  make docker-run           - Show example Docker run command"
	@echo ""
	@echo "Examples:"
	@echo "  make test                                    # Run all tests"
	@echo "  make test-file FILE=tests/test_loggers.py    # Run specific test"
	@echo "  make test-pattern PATTERN=test_extraction    # Run extraction tests"
	@echo "  make test-coverage                           # Generate coverage report"