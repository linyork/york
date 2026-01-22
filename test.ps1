###############################################################################
# York Test Execution Script (Windows PowerShell)
# This script runs tests in local environment, requires uv installation
###############################################################################

$ErrorActionPreference = "Stop"

# Check if uv is installed
try {
    $uvVersion = uv --version 2>$null
}
catch {
    Write-Host "❌ Error: 'uv' command not found." -ForegroundColor Red
    Write-Host "💡 Please install uv (Python package manager) first:" -ForegroundColor Yellow
    Write-Host "   PowerShell:" -ForegroundColor Cyan
    Write-Host "   irm https://astral.sh/uv/install.ps1 | iex" -ForegroundColor White
    Write-Host ""
    Write-Host "   Or visit: https://docs.astral.sh/uv/getting-started/installation/" -ForegroundColor Cyan
    exit 1
}

Write-Host "🔄 Syncing development environment dependencies..." -ForegroundColor Cyan
uv sync --frozen --extra dev

Write-Host ""
Write-Host "🧪 Starting Pytest..." -ForegroundColor Green
Write-Host "================================================================"

# Run tests
# -v: Verbose output
# --cov=src: Calculate coverage for src directory
# --cov-report=term-missing: Show missing lines in coverage report
uv run pytest tests/ -v --cov=src --cov-report=term-missing

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✅ Test execution completed!" -ForegroundColor Green
}
else {
    Write-Host ""
    Write-Host "❌ Tests failed!" -ForegroundColor Red
    exit 1
}
