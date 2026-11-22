# ADgents Package Build Script (Windows/PowerShell)
# Usage: .\scripts\build.ps1
# or:    .\scripts\build.ps1 -Publish $true
# or:    .\scripts\build.ps1 -TestOnly $true

param(
    [switch]$Clean = $false,
    [switch]$Publish = $false,
    [switch]$TestOnly = $false,
    [string]$Version = ""
)

Write-Host "🔨 ADgents Package Builder" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan

# Check for required tools
function Check-Tool {
    param([string]$Tool)
    try {
        $null = & $Tool --version
        Write-Host "✓ $Tool found" -ForegroundColor Green
        return $true
    }
    catch {
        Write-Host "✗ $Tool not found" -ForegroundColor Red
        return $false
    }
}

Write-Host ""
Write-Host "📋 Checking dependencies..." -ForegroundColor Yellow

# Check Python
if (-not (Check-Tool "python")) {
    Write-Host "Error: Python is required but not installed" -ForegroundColor Red
    exit 1
}

# Install build tools if needed
Write-Host ""
Write-Host "📦 Installing build tools..." -ForegroundColor Yellow
python -m pip install --quiet --upgrade pip
python -m pip install --quiet build wheel twine pytest pytest-cov

# Clean previous builds if requested
if ($Clean) {
    Write-Host ""
    Write-Host "🧹 Cleaning previous builds..." -ForegroundColor Yellow
    Remove-Item -Path "build" -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -Path "dist" -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -Path "*.egg-info" -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -Path ".pytest_cache" -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "✓ Cleaned" -ForegroundColor Green
}

# Run tests before building or exiting test-only mode.
Write-Host ""
Write-Host "🧪 Running tests..." -ForegroundColor Yellow
python -m pytest --tb=short
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Tests failed; stopping before build" -ForegroundColor Red
    exit $LASTEXITCODE
}
Write-Host "✓ Tests passed" -ForegroundColor Green

if ($TestOnly) {
    Write-Host ""
    Write-Host "✓ Tests completed" -ForegroundColor Green
    exit 0
}

# Update version if specified
if ($Version) {
    Write-Host ""
    Write-Host "📌 Updating version to $Version..." -ForegroundColor Yellow

    # Update pyproject.toml
    $content = Get-Content "pyproject.toml"
    $content = $content -replace 'version = "[^"]*"', "version = `"$Version`""
    Set-Content -Path "pyproject.toml" -Value $content

    Write-Host "✓ Version updated to $Version" -ForegroundColor Green
}

# Build package
Write-Host ""
Write-Host "🏗 Building package..." -ForegroundColor Yellow
python -m build
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Build successful" -ForegroundColor Green
}
else {
    Write-Host "✗ Build failed" -ForegroundColor Red
    exit 1
}

# Display built packages
Write-Host ""
Write-Host "📦 Built packages:" -ForegroundColor Cyan
Get-ChildItem -Path "dist" | ForEach-Object {
    Write-Host "  • $($_.Name) ($([math]::Round($_.Length / 1MB, 2)) MB)"
}

# Publish if requested
if ($Publish) {
    Write-Host ""
    Write-Host "🚀 Publishing to PyPI..." -ForegroundColor Yellow
    Write-Host "⚠ Note: Set TWINE_USERNAME and TWINE_PASSWORD environment variables" -ForegroundColor Yellow

    # Check for credentials
    if (-not $env:TWINE_USERNAME -or -not $env:TWINE_PASSWORD) {
        Write-Host "⚠ PyPI credentials not found in environment" -ForegroundColor Yellow
        Write-Host "   Set TWINE_USERNAME and TWINE_PASSWORD, or use API token:" -ForegroundColor Yellow
        Write-Host "   `$env:TWINE_USERNAME = '__token__'" -ForegroundColor Gray
        Write-Host "   `$env:TWINE_PASSWORD = 'pypi-xxxxx'" -ForegroundColor Gray
        return
    }

    python -m twine upload dist/* --non-interactive
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Published to PyPI" -ForegroundColor Green
    }
    else {
        Write-Host "✗ Publishing failed" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "================================" -ForegroundColor Cyan
Write-Host "✅ Build complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Install locally: pip install -e ." -ForegroundColor Gray
Write-Host "  2. Test: pip install dist/adgents-*.whl" -ForegroundColor Gray
Write-Host "  3. Publish: .\scripts\build.ps1 -Publish" -ForegroundColor Gray
Write-Host ""
