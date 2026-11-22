#!/usr/bin/env python3
"""
Quick reference for ADgents build system.
Run this to see build options.
"""

import subprocess
import sys
import platform

def print_header(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")

def show_help():
    os_type = platform.system()

    print_header("🔨 ADgents Build System Quick Reference")

    print("📦 BUILD COMMANDS\n")

    if os_type == "Windows":
        print("  # Windows (PowerShell)")
        print("  .\\scripts\\build.ps1              - Basic build")
        print("  .\\scripts\\build.ps1 -Clean       - Clean build")
        print("  .\\scripts\\build.ps1 -Publish     - Build & publish to PyPI")
        print("  .\\scripts\\build.ps1 -TestOnly    - Run tests only")
        print("  .\\scripts\\build.ps1 -Version 1.1.0 -Publish\n")
    else:
        print("  # Linux/Mac (Bash)")
        print("  ./scripts/build.sh                 - Basic build")
        print("  ./scripts/build.sh --clean         - Clean build")
        print("  ./scripts/build.sh --publish       - Build & publish to PyPI")
        print("  ./scripts/build.sh --test-only     - Run tests only")
        print("  ./scripts/build.sh --version 1.1.0 --publish\n")

    print("  # All Platforms (Makefile)")
    print("  make build              - Build the package")
    print("  make test               - Run tests")
    print("  make clean              - Clean build artifacts")
    print("  make publish            - Publish to PyPI")
    print("  make install            - Install locally")
    print("  make lint               - Run code quality checks")
    print("  make help               - Show all make commands\n")

    print_header("📚 AUTOMATED BUILDS (GitHub Actions)")
    print("Triggered automatically on:\n")
    print("  1. Version tags:  git push origin v1.0.0")
    print("  2. Releases:      Create release on GitHub")
    print("  3. Manual:        GitHub Actions → Run workflow\n")

    print_header("📝 SETUP FOR AUTOMATIC PUBLISHING")
    print("1. Create PyPI account:    https://pypi.org/register/")
    print("2. Generate API token:     https://pypi.org/manage/account/credentials/")
    print("3. Add to GitHub Secrets:  https://github.com/CYBERBULL123/ADgents/settings/secrets/actions")
    print("   - Name:  PYPI_API_TOKEN")
    print("   - Value: pypi-xxxxx\n")

    print_header("🚀 QUICK RELEASE WORKFLOW")
    print("# 1. Update version (optional)")
    print("make version-patch    # 1.0.0 → 1.0.1")
    print("# or edit pyproject.toml\n")

    print("# 2. Run tests")
    print("make test\n")

    print("# 3. Commit changes")
    print("git add pyproject.toml")
    print("git commit -m 'Release v1.0.1'")
    print("git push origin main\n")

    print("# 4. Push tag (auto-builds and publishes!)")
    print("git tag v1.0.1")
    print("git push origin v1.0.1\n")

    print_header("📦 BUILD ARTIFACTS")
    print("After building, check dist/ folder:\n")
    print("  dist/adgents-1.0.0-py3-none-any.whl")
    print("  dist/adgents-1.0.0.tar.gz\n")

    print("Install locally for testing:")
    if os_type == "Windows":
        print("  pip install dist\\adgents-*.whl\n")
    else:
        print("  pip install dist/adgents-*.whl\n")

    print_header("📖 DOCUMENTATION")
    print("See these files for detailed information:\n")
    print("  • RELEASE.md - Complete release guide")
    print("  • BUILD.md   - Quick build reference")
    print("  • README.md  - Main documentation\n")

    print_header("✅ Quick Test")
    print("After building locally:\n")
    if os_type == "Windows":
        print("  pip install .\\dist\\adgents-*.whl")
    else:
        print("  pip install ./dist/adgents-*.whl")
    print("  python -c \"import adgents; print('✓ Package installed successfully')\"")
    print("  pip uninstall adgents -y\n")

if __name__ == "__main__":
    show_help()

    print("\n💡 TIP: Run 'make help' for all available commands\n")
