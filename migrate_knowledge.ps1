###############################################################################
# Knowledge Migration and Reindexing Tool (Windows PowerShell)
# Purpose: Trigger York to rescan and rebuild vector index
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

Write-Host "🔄 Starting knowledge base reindexing..." -ForegroundColor Cyan
Write-Host "This may take some time depending on the number of files." -ForegroundColor Yellow

# Python code for reindexing
$pythonCode = @"
import asyncio
import sys
sys.path.insert(0, '/app')
from src.knowledge.sync import reindex_all_projects
from src.utils.logger import Logger

async def main():
    Logger.info('Migrate', 'Starting full reindex...')
    results = await reindex_all_projects()
    
    total_count = 0
    total_errors = 0
    
    for project, stats in results.items():
        count = stats.get('count', 0)
        errors = stats.get('errors', 0)
        total_count += count
        total_errors += errors
        print(f'Project {project}: {count} files, {errors} errors')
        
    Logger.success('Migrate', f'Migration complete! Total {total_count} files, {total_errors} errors')

if __name__ == '__main__':
    asyncio.run(main())
"@

# Run migration using Docker
docker run -it --rm `
    -v "${projectsPath}:${CONTAINER_PROJECTS_DIR}" `
    -v "${knowledgePath}:${CONTAINER_KNOWLEDGE_ROOT}" `
    -e PROJECTS_DIR="$CONTAINER_PROJECTS_DIR" `
    -e YORK_KNOWLEDGE_ROOT="$CONTAINER_KNOWLEDGE_ROOT" `
    $IMAGE_NAME `
    python -c $pythonCode
