# Makefile for OpenHands Server

.PHONY: help install install-dev install-build test lint format type-check clean build-binary run

# Default target
help:
	@echo "Available targets:"
	@echo "  install      - Install the package"
	@echo "  install-dev  - Install with development dependencies"
	@echo "  install-build - Install with build dependencies"
	@echo "  test         - Run tests"
	@echo "  lint         - Run linting"
	@echo "  format       - Format code"
	@echo "  type-check   - Run type checking"
	@echo "  build-binary - Build PyInstaller binary"
	@echo "  clean        - Clean build artifacts"
	@echo "  run          - Run the server in development mode"

# Installation targets
install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"

install-build:
	pip install -e ".[build]"

# Development targets
test:
	pytest

lint:
	ruff check .

format:
	ruff format .

type-check:
	pyright

# Build targets
build-binary: install-build
	@echo "Building PyInstaller binary..."
	pyinstaller openhands-server.spec
	@echo "Binary built: dist/openhands-server"

# Clean targets
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf __pycache__/
	find . -name "*.pyc" -delete
	find . -name "*.pyo" -delete
	find . -name "__pycache__" -type d -exec rm -rf {} +

# Development server
run:
	@echo "Starting development server..."
	@echo "Make sure OPENHANDS_MASTER_KEY is set!"
	python -m openhands.server.cli --host 0.0.0.0 --port 8000 --reload

# Test the binary
test-binary: build-binary
	@echo "Testing binary..."
	./dist/openhands-server --help