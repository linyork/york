###############################################################################
# York Knowledge Watcher (Windows PowerShell)
# Purpose: Real-time sync of local knowledge base changes to Cloud
###############################################################################

$ErrorActionPreference = "Stop"

# Configuration
# =============================================================================
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Load settings from .env
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

# Determine paths
$LocalKnowledge = Join-Path $ScriptDir "york-knowledge"
if ($env:YORK_KNOWLEDGE_ROOT) {
    if ($env:YORK_KNOWLEDGE_ROOT -match "^\.") {
        $LocalKnowledge = Join-Path $ScriptDir $env:YORK_KNOWLEDGE_ROOT
    }
    else {
        $LocalKnowledge = $env:YORK_KNOWLEDGE_ROOT
    }
}

$CloudDrivePath = $env:REMOTE_KNOWLEDGE_ROOT

if ([string]::IsNullOrWhiteSpace($CloudDrivePath)) {
    Write-Host "⚠️  REMOTE_KNOWLEDGE_ROOT not set. Watcher exiting."
    exit 1
}

# =============================================================================

Write-Host "👀 Watching for changes in: $LocalKnowledge" -ForegroundColor Cyan
Write-Host "☁️  Target: $CloudDrivePath" -ForegroundColor Cyan

# Define the watcher
$watcher = New-Object System.IO.FileSystemWatcher
$watcher.Path = $LocalKnowledge
$watcher.IncludeSubdirectories = $true
$watcher.EnableRaisingEvents = $true

# Sync Logic
$Action = {
    $path = $Event.SourceEventArgs.FullPath
    $changeType = $Event.SourceEventArgs.ChangeType
    $timeStamp = Get-Date -Format "HH:mm:ss"

    # Filter out temp files or internal git operations if needed
    if ($path -match "\.tmp$" -or $path -match "~$") { return }

    Write-Host "[$timeStamp] $changeType detected: $path" -ForegroundColor Yellow
    
    # Debounce: Wait a bit to avoid triggering multiple times for same file
    # Simple implementation: Just run Robocopy
    # /MIR might be too aggressive for single file changes, but it ensures consistency
    # We use /M (copy files with Archive attribute) or just simple copy for performance?
    # For safety and consistency, we stick to MIR but we make it quiet
    
    $robocopyArgs = @(
        $LocalKnowledge,
        $CloudDrivePath,
        "/MIR", "/R:1", "/W:1", "/MT:4", "/NFL", "/NDL", "/NJH", "/NJS"
    )

    try {
        Start-Process -FilePath "robocopy.exe" -ArgumentList $robocopyArgs -NoNewWindow -Wait
        Write-Host "   ✅ Synced to Cloud" -ForegroundColor Green
    }
    catch {
        Write-Host "   ❌ Sync Failed" -ForegroundColor Red
    }
}

# Register Events
Register-ObjectEvent $watcher "Created" -Action $Action | Out-Null
Register-ObjectEvent $watcher "Changed" -Action $Action | Out-Null
Register-ObjectEvent $watcher "Deleted" -Action $Action | Out-Null
Register-ObjectEvent $watcher "Renamed" -Action $Action | Out-Null

Write-Host "✅ Watcher Service Started. Press Ctrl+C to stop." -ForegroundColor Green

# Keep script running
try {
    while ($true) {
        Start-Sleep -Seconds 1
    }
}
finally {
    Unregister-Event -SourceIdentifier "Created" -ErrorAction SilentlyContinue
    Unregister-Event -SourceIdentifier "Changed" -ErrorAction SilentlyContinue
    Unregister-Event -SourceIdentifier "Deleted" -ErrorAction SilentlyContinue
    Unregister-Event -SourceIdentifier "Renamed" -ErrorAction SilentlyContinue
    $watcher.Dispose()
    Write-Host "Watcher Stopped."
}
