#!/bin/bash
# ADgents Package Build Script (Unix/Linux/Mac)
# Usage: ./scripts/build.sh
# or:    ./scripts/build.sh --publish
# or:    ./scripts/build.sh --test-only

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

CLEAN=false
PUBLISH=false
TEST_ONLY=false
VERSION=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --clean) CLEAN=true; shift ;;
        --publish) PUBLISH=true; shift ;;
        --test-only) TEST_ONLY=true; shift ;;
        --version) VERSION="$2"; shift 2 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

echo -e "${CYAN}🔨 ADgents Package Builder${NC}"
echo -e "${CYAN}================================${NC}"

# Check for required tools
check_tool() {
    if ! command -v $1 &> /dev/null; then
        echo -e "${RED}✗ $1 not found${NC}"
        return 1
    fi
    echo -e "${GREEN}✓ $1 found${NC}"
    return 0
}

echo ""
echo -e "${YELLOW}📋 Checking dependencies...${NC}"

if ! check_tool python3; then
    echo -e "${RED}Error: Python3 is required but not installed${NC}"
    exit 1
fi

# Install build tools
echo ""
echo -e "${YELLOW}📦 Installing build tools...${NC}"
python3 -m pip install --quiet --upgrade pip
python3 -m pip install --quiet build wheel twine pytest pytest-cov

# Clean if requested
if [ "$CLEAN" = true ]; then
    echo ""
    echo -e "${YELLOW}🧹 Cleaning previous builds...${NC}"
    rm -rf build dist *.egg-info .pytest_cache
    echo -e "${GREEN}✓ Cleaned${NC}"
fi

# Run tests before building or exiting test-only mode.
echo ""
echo -e "${YELLOW}🧪 Running tests...${NC}"
if python3 -m pytest --tb=short; then
    echo -e "${GREEN}✓ Tests passed${NC}"
else
    echo -e "${RED}✗ Tests failed; stopping before build${NC}"
    exit 1
fi

if [ "$TEST_ONLY" = true ]; then
    echo ""
    echo -e "${GREEN}✓ Tests completed${NC}"
    exit 0
fi

# Update version if specified
if [ -n "$VERSION" ]; then
    echo ""
    echo -e "${YELLOW}📌 Updating version to $VERSION...${NC}"

    # Update pyproject.toml
    sed -i.bak "s/version = \"[^\"]*\"/version = \"$VERSION\"/" pyproject.toml
    rm -f pyproject.toml.bak

    echo -e "${GREEN}✓ Version updated to $VERSION${NC}"
fi

# Build package
echo ""
echo -e "${YELLOW}🏗 Building package...${NC}"
if python3 -m build; then
    echo -e "${GREEN}✓ Build successful${NC}"
else
    echo -e "${RED}✗ Build failed${NC}"
    exit 1
fi

# Display built packages
echo ""
echo -e "${CYAN}📦 Built packages:${NC}"
ls -lh dist/ | tail -n +2 | awk '{print "  • " $9 " (" $5 ")"}'

# Publish if requested
if [ "$PUBLISH" = true ]; then
    echo ""
    echo -e "${YELLOW}🚀 Publishing to PyPI...${NC}"
    echo -e "${YELLOW}⚠ Note: Set TWINE_USERNAME and TWINE_PASSWORD environment variables${NC}"

    if [ -z "$TWINE_USERNAME" ] || [ -z "$TWINE_PASSWORD" ]; then
        echo -e "${YELLOW}⚠ PyPI credentials not found in environment${NC}"
        echo -e "${YELLOW}   Set TWINE_USERNAME and TWINE_PASSWORD, or use API token:${NC}"
        echo -e "${RED}   export TWINE_USERNAME='__token__'${NC}"
        echo -e "${RED}   export TWINE_PASSWORD='pypi-xxxxx'${NC}"
        exit 1
    fi

    if python3 -m twine upload dist/* --non-interactive; then
        echo -e "${GREEN}✓ Published to PyPI${NC}"
    else
        echo -e "${RED}✗ Publishing failed${NC}"
        exit 1
    fi
fi

echo ""
echo -e "${CYAN}================================${NC}"
echo -e "${GREEN}✅ Build complete!${NC}"
echo ""
echo -e "${CYAN}Next steps:${NC}"
echo -e "${RED}  1. Install locally: pip install -e .${NC}"
echo -e "${RED}  2. Test: pip install dist/adgents-*.whl${NC}"
echo -e "${RED}  3. Publish: ./scripts/build.sh --publish${NC}"
echo ""
