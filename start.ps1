###############################################################################
# York Startup Script (Docker Version - Windows PowerShell)
# Target: Windows (Antigravity/Claude Desktop)
#
# Workflows:
# 1. Startup Sync: Pull changes from Cloud (SSOT) -> Local
# 2. Watcher Service: Start background job for real-time sync (Local -> Cloud)
# 3. Docker Container: Run York MCP Server
# 4. Cleanup: Stop watcher and perform final backup on exit
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
    $env:YORK_KNOWLEDGE_ROOT = Join-Path $ScriptDir "york-knowledge"
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

# 強制初始化同步：Cloud -> Local
# 策略：雲端為單一真理來源 (SSOT)。每次啟動先拉取最新資料。
if ($env:REMOTE_KNOWLEDGE_ROOT -and (Test-Path $env:REMOTE_KNOWLEDGE_ROOT)) {
    [Console]::Error.WriteLine("[Script] Performing startup sync (Cloud -> Local)...")
    
    # 使用 Robocopy /MIR 確保本地與雲端完全一致
    # /MIR: Mirror (複製所有內容，並刪除本地多餘檔案)
    $robocopyArgs = @(
        $env:REMOTE_KNOWLEDGE_ROOT, 
        $env:YORK_KNOWLEDGE_ROOT, 
        "/MIR", "/R:1", "/W:1", "/MT:4", "/NFL", "/NDL", "/NJH", "/NJS"
    )
    
    
    # 執行同步 (Redirect all output to null)
    # Using Call Operator & with *>$null is safer and simpler than Start-Process redirection
    & robocopy.exe $robocopyArgs *>$null
    if ($LASTEXITCODE -ge 8) {
        # Robocopy exit code >= 8 means failure
        [Console]::Error.WriteLine("[Script] Startup sync FAILED with code $LASTEXITCODE")
        exit 1
    }
    [Console]::Error.WriteLine("[Script] Startup sync completed.")
}

# Start Watcher Service in Background
# Notice: All user-facing logs are sent to Write-Warning to avoid polluting stdout (MCP protocol)
$WatcherScript = Join-Path $ScriptDir "watch_sync.ps1"
$WatcherJob = $null

if (Test-Path $WatcherScript) {
    # Start as a background job
    $WatcherJob = Start-Job -ScriptBlock {
        param($File)
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $File
    } -ArgumentList $WatcherScript
}

# Start Docker container with Auto-backup protection
try {
    # Ensure any previous instance is removed to avoid name conflicts
    # Check existence to avoid error if container is already gone
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
    # Stop Watcher Service
    if ($WatcherJob) {
        Stop-Job $WatcherJob
        Remove-Job $WatcherJob
    }

    # Final Auto-backup (Safety Net)
    # Output redirection *>$null ensures no random output breaks MCP shutdown sequence
    $SyncScript = Join-Path $ScriptDir "sync_knowledge.ps1"
    if (Test-Path $SyncScript) {
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $SyncScript "auto-backup" *>$null
    }
}
