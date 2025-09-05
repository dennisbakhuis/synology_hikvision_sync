# Makefile for Synology Camera Sync Scripts
# Author: Dennis Bakhuis
# Date: 2025-09-05

.PHONY: test test-sync test-retention syntax-check install clean help

# Default target
all: syntax-check test

# Run all tests
test: test-sync test-retention
	@echo "✅ All tests completed successfully"

# Run sync script tests
test-sync:
	@echo "🧪 Running sync camera tests..."
	@bats tests/test_sync_camera.bats

# Run retention script tests  
test-retention:
	@echo "🧪 Running retention policy tests..."
	@bats tests/test_retention.bats

# Check script syntax without execution
syntax-check:
	@echo "🔍 Checking script syntax..."
	@bash -n src/sync_camera_synology.sh && echo "  ✓ src/sync_camera_synology.sh syntax OK"
	@bash -n src/apply_camera_retention.sh && echo "  ✓ src/apply_camera_retention.sh syntax OK"
	@bash -n tests/setup_test_data.sh && echo "  ✓ tests/setup_test_data.sh syntax OK"

# Install scripts to /usr/local/bin (for local development)
install:
	@echo "📦 Installing scripts to /usr/local/bin..."
	@sudo cp src/sync_camera_synology.sh /usr/local/bin/
	@sudo cp src/apply_camera_retention.sh /usr/local/bin/
	@sudo chmod +x /usr/local/bin/sync_camera_synology.sh
	@sudo chmod +x /usr/local/bin/apply_camera_retention.sh
	@echo "  ✓ Scripts installed successfully"

# Install to Synology NAS (requires SYNOLOGY_HOST environment variable)
install-synology:
	@if [ -z "$(SYNOLOGY_HOST)" ]; then \
		echo "❌ Error: Set SYNOLOGY_HOST environment variable"; \
		echo "   Example: make install-synology SYNOLOGY_HOST=admin@192.168.1.100"; \
		exit 1; \
	fi
	@echo "📡 Installing scripts to Synology NAS..."
	@ssh $(SYNOLOGY_HOST) "mkdir -p /volume1/scripts"
	@scp src/sync_camera_synology.sh $(SYNOLOGY_HOST):/volume1/scripts/
	@scp src/apply_camera_retention.sh $(SYNOLOGY_HOST):/volume1/scripts/
	@ssh $(SYNOLOGY_HOST) "chmod +x /volume1/scripts/sync_camera_synology.sh"
	@ssh $(SYNOLOGY_HOST) "chmod +x /volume1/scripts/apply_camera_retention.sh"
	@echo "  ✓ Scripts installed to $(SYNOLOGY_HOST):/volume1/scripts/"

# Create test data for manual testing
test-data:
	@echo "🗂️  Creating test data..."
	@./tests/setup_test_data.sh ./test_data_output
	@echo "  ✓ Test data created in ./test_data_output"
	@echo "  💡 Edit scripts to use test paths, then run them safely"

# Clean up test data and temporary files
clean:
	@echo "🧹 Cleaning up..."
	@rm -rf ./test_data_output
	@rm -f /tmp/sync_camera_synology.lock
	@rm -f /tmp/apply_camera_retention.lock
	@find . -name "*.bats.tmp*" -delete 2>/dev/null || true
	@echo "  ✓ Cleanup completed"

# Run tests with pretty output
test-pretty: 
	@echo "🎨 Running tests with pretty output..."
	@bats tests/test_sync_camera.bats -p
	@echo ""
	@bats tests/test_retention.bats -p

# Check if bats is installed
check-deps:
	@echo "🔧 Checking dependencies..."
	@command -v bats >/dev/null || { \
		echo "❌ bats not found. Install with:"; \
		echo "   macOS: brew install bats-core"; \
		echo "   Linux: git clone https://github.com/bats-core/bats-core.git && sudo ./bats-core/install.sh /usr/local"; \
		exit 1; \
	}
	@echo "  ✓ bats is installed"
	@bats --version

# Show usage information
help:
	@echo "Synology Camera Sync Scripts - Available Commands:"
	@echo ""
	@echo "  make test              - Run all tests (syntax + bats tests)"
	@echo "  make test-sync         - Run sync script tests only"  
	@echo "  make test-retention    - Run retention script tests only"
	@echo "  make test-pretty       - Run tests with colorized output"
	@echo "  make syntax-check      - Check bash syntax without execution"
	@echo ""
	@echo "  make test-data         - Create test data for manual testing"
	@echo "  make clean             - Clean up test data and temp files"
	@echo ""
	@echo "  make install           - Install scripts to /usr/local/bin"
	@echo "  make install-synology  - Install to Synology NAS"
	@echo "                           Usage: make install-synology SYNOLOGY_HOST=admin@192.168.1.100"
	@echo ""
	@echo "  make check-deps        - Check if required tools are installed"
	@echo "  make help              - Show this help message"
	@echo ""
	@echo "Examples:"
	@echo "  make test                                    # Run all tests"
	@echo "  make install-synology SYNOLOGY_HOST=admin@nas.local"
	@echo "  make test-data && vim sync_camera_synology.sh # Create test env"