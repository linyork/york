###############################################################################
# York Startup Script (Docker Version - Windows PowerShell)
# Target: Windows (Antigravity/Claude Desktop)
###############################################################################

# Set output encoding to UTF-8 to prevent encoding issues
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

$ErrorActionPreference = "Stop"

# Get script directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

# Load .env file
$envFile = Join-Path $ScriptDir ".env"
if (Test-Path $envFile) {
    Get-Content $envFile -Encoding UTF8 | ForEach-Object {
        if ($_ -match '^([^#][^=]+)=(.*)$') {
            $key = $matches[1].Trim()
            $value = $matches[2].Trim()
            [Environment]::SetEnvironmentVariable($key, $value, "Process")
        }
    }
}

# Set default environment variables if not loaded from .env
if (-not $env:PROJECTS_DIR) {
    $env:PROJECTS_DIR = "c:/Users/User/Documents/git"
}
if (-not $env:YORK_KNOWLEDGE_ROOT) {
    $env:YORK_KNOWLEDGE_ROOT = Join-Path $ScriptDir ".data"
}
if (-not $env:LOG_LEVEL) {
    $env:LOG_LEVEL = "info"
}
if (-not $env:NODE_ENV) {
    $env:NODE_ENV = "production"
}

# Ensure knowledge directory exists
if (-not (Test-Path $env:YORK_KNOWLEDGE_ROOT)) {
    New-Item -ItemType Directory -Path $env:YORK_KNOWLEDGE_ROOT -Force | Out-Null
}

# Define container internal paths
$CONTAINER_PROJECTS_DIR = "/projects"
$CONTAINER_KNOWLEDGE_ROOT = "/knowledge"

# Convert Windows paths to Docker-compatible format
$projectsPath = $env:PROJECTS_DIR -replace '\\', '/' -replace '^([A-Z]):', '/$1'
$knowledgePath = $env:YORK_KNOWLEDGE_ROOT -replace '\\', '/' -replace '^([A-Z]):', '/$1'

# Start Docker container
try {
    # Ensure any previous instance is removed to avoid name conflicts
    if (docker ps -a -q -f "name=york-mcp") {
        docker rm -f york-mcp | Out-Null
    }

    # -i: Keep STDIN open (required for MCP)
    # --rm: Auto-remove container after stop
    docker run -i --rm `
        --name york-mcp `
        -v "${projectsPath}:${CONTAINER_PROJECTS_DIR}" `
        -v "${knowledgePath}:${CONTAINER_KNOWLEDGE_ROOT}" `
        -e PROJECTS_DIR="$CONTAINER_PROJECTS_DIR" `
        -e YORK_KNOWLEDGE_ROOT="$CONTAINER_KNOWLEDGE_ROOT" `
        -e ALLOWED_PROJECTS="$env:ALLOWED_PROJECTS" `
        -e LOG_LEVEL="$env:LOG_LEVEL" `
        -e NODE_ENV="$env:NODE_ENV" `
        mcp/york
}
finally {
}
