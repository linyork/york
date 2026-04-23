###############################################################################
# York Installation Wizard (Docker Version - Windows PowerShell)
# Purpose: Initialize environment, generate config and build Docker Image
###############################################################################

$ErrorActionPreference = "Stop"

# Get script directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

# Color definitions using Write-Host colors
function Write-Header {
    Write-Host ""
    Write-Host "╔════════════════════════════════════════╗" -ForegroundColor Blue
    Write-Host "║   🐳 York MCP Server Setup (Docker)  ║" -ForegroundColor Blue
    Write-Host "╚════════════════════════════════════════╝" -ForegroundColor Blue
    Write-Host ""
}

function Write-Success {
    param([string]$Message)
    Write-Host "✓ $Message" -ForegroundColor Green
}

function Write-Info {
    param([string]$Message)
    Write-Host $Message -ForegroundColor Blue
}

function Write-Warning {
    param([string]$Message)
    Write-Host $Message -ForegroundColor Yellow
}

function Write-Error-Message {
    param([string]$Message)
    Write-Host "❌ $Message" -ForegroundColor Red
}

Write-Header

# Check Docker
Write-Info "📋 Checking environment requirements..."

try {
    $dockerVersion = docker --version
    Write-Success "Docker installed: $dockerVersion"
}
catch {
    Write-Error-Message "Docker not found"
    Write-Host "Please install Docker Desktop first: https://www.docker.com/products/docker-desktop"
    exit 1
}

# Interactive setup
Write-Host ""
Write-Info "⚙️  Environment variable configuration"
Write-Host ""

# PROJECTS_DIR
if (-not $env:PROJECTS_DIR) {
    $defaultProjectsDir = "$env:USERPROFILE\Documents\git"
    $projectsDirInput = Read-Host "Project root directory path (default: $defaultProjectsDir)"
    if ([string]::IsNullOrWhiteSpace($projectsDirInput)) {
        $env:PROJECTS_DIR = $defaultProjectsDir
    }
    else {
        $env:PROJECTS_DIR = $projectsDirInput
    }
}

Write-Success "Project root directory: $($env:PROJECTS_DIR)"

# YORK_KNOWLEDGE_ROOT
if (-not $env:YORK_KNOWLEDGE_ROOT) {
    $defaultKnowledgeRoot = Join-Path $ScriptDir "york-knowledge"
    $knowledgeRootInput = Read-Host "Knowledge base path (default: $defaultKnowledgeRoot)"
    if ([string]::IsNullOrWhiteSpace($knowledgeRootInput)) {
        $env:YORK_KNOWLEDGE_ROOT = $defaultKnowledgeRoot
    }
    else {
        $env:YORK_KNOWLEDGE_ROOT = $knowledgeRootInput
    }
}

if (-not (Test-Path $env:YORK_KNOWLEDGE_ROOT)) {
    New-Item -ItemType Directory -Path $env:YORK_KNOWLEDGE_ROOT -Force | Out-Null
}
Write-Success "Knowledge base path: $($env:YORK_KNOWLEDGE_ROOT)"

# Create .env file
Write-Host ""
Write-Info "📝 Generating .env file..."

$envContent = @"
# York Environment Configuration
# Project root directory
PROJECTS_DIR=$($env:PROJECTS_DIR)

# Knowledge base storage path (Local Docker mount)
YORK_KNOWLEDGE_ROOT=$($env:YORK_KNOWLEDGE_ROOT)

ALLOWED_PROJECTS=
LOG_LEVEL=info
NODE_ENV=production
"@

$envContent | Out-File -FilePath ".env" -Encoding UTF8 -Force
Write-Success ".env file created"

# Build Docker Image
Write-Host ""
Write-Info "🔨 Starting Docker Image build..."
Write-Warning "(This may take several minutes)"
Write-Host ""

$buildScript = Join-Path $ScriptDir "build-image.ps1"
if (Test-Path $buildScript) {
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $buildScript
}
else {
    Write-Error-Message "build-image.ps1 not found"
    exit 1
}

# Generate MCP configuration
Write-Host ""
Write-Info "🔧 Generating MCP configuration..."
Write-Host ""

$startScriptPath = Join-Path $ScriptDir "start.ps1"
$startScriptPath = $startScriptPath -replace '\\', '/'

Write-Host "Please add the following configuration to your Antigravity MCP config file:" -ForegroundColor Cyan
Write-Host ""
Write-Host "{"
Write-Host '  "mcpServers": {'
Write-Host '    "york": {'
Write-Host '      "command": "powershell.exe",'
Write-Host '      "args": ['
Write-Host '        "-NoProfile",'
Write-Host '        "-ExecutionPolicy",'
Write-Host '        "Bypass",'
Write-Host '        "-File",'
Write-Host "        `"$startScriptPath`""
Write-Host '      ]'
Write-Host '    }'
Write-Host '  }'
Write-Host "}"
Write-Host ""
Write-Host "Antigravity MCP config file location:" -ForegroundColor Yellow
Write-Host "  $env:USERPROFILE\.gemini\antigravity\mcp_config.json"
Write-Host ""

Write-Success "✅ Installation completed!"
Write-Host ""
Write-Host "Run '.\start.ps1' to test startup" -ForegroundColor Cyan
Write-Host ""
