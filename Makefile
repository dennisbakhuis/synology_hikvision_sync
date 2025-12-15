# Makefile for Synology Hikvision Sync
# Author: Dennis Bakhuis
# Date: 2025-09-06

.PHONY: test docker types help

all: help

test:
	@echo "🧪 Running tests..."
	@uv run pytest

docker:
	@echo "🐳 Building Docker image..."
	@docker build -t synology_hikvision_sync .

types:
	@uv run mypy .

help:
	@echo "Synology Hikvision Sync - Available Commands:"
	@echo ""
	@echo "🧪 Testing:"
	@echo "  make test             - Run all tests"
	@echo ""
	@echo "🔧 Development:"
	@echo "  make types            - Run type checking"
	@echo "  make clean            - Clean up temporary files and caches"
	@echo ""
	@echo "🐳 Docker:"
	@echo "  make docker-build     - Build Docker image"
