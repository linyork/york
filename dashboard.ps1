###############################################################################
# York Knowledge Dashboard (Windows PowerShell)
###############################################################################

$ErrorActionPreference = "Stop"

# Define image name
$IMAGE_NAME = "mcp/york"

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

# Set default values
if (-not $env:PROJECTS_DIR) {
    $env:PROJECTS_DIR = "$env:USERPROFILE\Documents\git"
}
if (-not $env:YORK_KNOWLEDGE_ROOT) {
    $env:YORK_KNOWLEDGE_ROOT = Join-Path $ScriptDir "york-knowledge"
}

# Define container internal paths
$CONTAINER_PROJECTS_DIR = "/projects"
$CONTAINER_KNOWLEDGE_ROOT = "/knowledge"

# Convert Windows paths to Docker-compatible format
$projectsPath = $env:PROJECTS_DIR -replace '\\', '/' -replace '^([A-Z]):', '/$1'
$knowledgePath = $env:YORK_KNOWLEDGE_ROOT -replace '\\', '/' -replace '^([A-Z]):', '/$1'

Write-Host "🚀 Starting York Knowledge Dashboard..." -ForegroundColor Cyan
Write-Host "🌐 http://localhost:8501" -ForegroundColor Green

# Run Streamlit using Docker
docker run -it --rm `
    -p 8501:8501 `
    -v "${projectsPath}:${CONTAINER_PROJECTS_DIR}" `
    -v "${knowledgePath}:${CONTAINER_KNOWLEDGE_ROOT}" `
    -e PROJECTS_DIR="$CONTAINER_PROJECTS_DIR" `
    -e YORK_KNOWLEDGE_ROOT="$CONTAINER_KNOWLEDGE_ROOT" `
    $IMAGE_NAME `
    streamlit run src/scripts/dashboard.py --server.address 0.0.0.0
