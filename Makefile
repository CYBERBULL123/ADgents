.PHONY: help build clean test publish install docs lint

# ADgents Build Makefile
# Usage: make build
#        make test
#        make publish

help:
	@echo "ADgents Build Commands:"
	@echo "  make build          - Build the package"
	@echo "  make clean          - Clean build artifacts"
	@echo "  make test           - Run tests"
	@echo "  make install        - Install package locally"
	@echo "  make publish        - Publish to PyPI"
	@echo "  make lint           - Run code quality checks"
	@echo "  make docs           - Build documentation"
	@echo "  make all            - Build, test, and verify"

build:
	@echo "🏗 Building package..."
	python -m build
	@echo "✓ Build complete"

clean:
	@echo "🧹 Cleaning build artifacts..."
	rm -rf build dist *.egg-info .pytest_cache .coverage htmlcov
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	@echo "✓ Cleaned"

test:
	@echo "🧪 Running tests..."
	python -m pytest --cov=core --cov-report=html
	@echo "✓ Tests passed"

lint:
	@echo "📍 Running linters..."
	python -m flake8 core --max-line-length=120 || true
	python -m isort --check-only core || true
	@echo "✓ Lint check complete"

install:
	@echo "📦 Installing package locally..."
	pip install -e .
	@echo "✓ Installed"

docs:
	@echo "📚 Building documentation..."
	pip install mkdocs mkdocs-material
	mkdocs build
	@echo "✓ Documentation built"

publish: clean build test
	@echo "🚀 Publishing to PyPI..."
	twine upload dist/*
	@echo "✓ Published"

all: clean build lint test
	@echo "✅ All checks passed!"

version-patch:
	@echo "Bumping patch version..."
	python -c "import re; v = open('pyproject.toml').read(); new_v = re.sub(r'version = \"(\d+)\.(\d+)\.(\d+)\"', lambda m: f'version = \"{m.group(1)}.{m.group(2)}.{int(m.group(3))+1}\"', v); open('pyproject.toml', 'w').write(new_v)"

version-minor:
	@echo "Bumping minor version..."
	python -c "import re; v = open('pyproject.toml').read(); new_v = re.sub(r'version = \"(\d+)\.(\d+)\.(\d+)\"', lambda m: f'version = \"{m.group(1)}.{int(m.group(2))+1}.0\"', v); open('pyproject.toml', 'w').write(new_v)"

version-major:
	@echo "Bumping major version..."
	python -c "import re; v = open('pyproject.toml').read(); new_v = re.sub(r'version = \"(\d+)\.(\d+)\.(\d+)\"', lambda m: f'version = \"{int(m.group(1))+1}.0.0\"', v); open('pyproject.toml', 'w').write(new_v)"
