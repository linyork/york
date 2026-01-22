###############################################################################
# York Knowledge Sync Tool (Windows PowerShell)
# Purpose: Sync local knowledge base to Google Drive (G:) as backup
###############################################################################

$ErrorActionPreference = "Stop"

# Configuration
# =============================================================================
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$LocalKnowledge = Join-Path $ScriptDir "york-knowledge"

# Load settings from .env
$envFile = Join-Path $ScriptDir ".env"
if (Test-Path $envFile) {
    Get-Content $envFile -Encoding UTF8 | ForEach-Object {
        if ($_ -match '^([^#][^=]+)=(.*)$') {
            $key = $matches[1].Trim()
            $value = $matches[2].Trim()
            
            # Load into process env for easy access
            [Environment]::SetEnvironmentVariable($key, $value, "Process")
        }
    }
}

# Determine paths
if ($env:YORK_KNOWLEDGE_ROOT) {
    # Resolve relative path if needed
    if ($env:YORK_KNOWLEDGE_ROOT -match "^\.") {
        $LocalKnowledge = Join-Path $ScriptDir $env:YORK_KNOWLEDGE_ROOT
    }
    else {
        $LocalKnowledge = $env:YORK_KNOWLEDGE_ROOT
    }
}

$CloudDrivePath = $env:REMOTE_KNOWLEDGE_ROOT
# =============================================================================

if ([string]::IsNullOrWhiteSpace($CloudDrivePath)) {
    Write-Host "⚠️  REMOTE_KNOWLEDGE_ROOT not set in .env" -ForegroundColor Yellow
    Write-Host "   Please set it to your Cloud Drive path (e.g. G:\My Drive\knowledge)"
    if ($args[0] -eq "auto-backup") { exit } # Exit silently on auto-backup
    exit 1
}

function Write-Log {
    param([string]$Message, [string]$Color = "White")
    Write-Host "[Sync] $Message" -ForegroundColor $Color
}

function Sync-To-Cloud {
    Write-Log "Preparing to sync Local -> Cloud (Backup)..." "Cyan"
    
    if (-not (Test-Path $CloudDrivePath)) {
        Write-Log "Cloud path not found, creating: $CloudDrivePath" "Yellow"
        New-Item -ItemType Directory -Path $CloudDrivePath -Force | Out-Null
    }

    # Robocopy arguments
    # /MIR : Mirror a directory tree (equivalent to /E plus /PURGE).
    # /R:3 : Retry 3 times on failed copies.
    # /W:2 : Wait 2 seconds between retries.
    # /MT:8 : Multi-threaded copying (8 threads).
    # /NJH : No Job Header.
    # /NJS : No Job Summary (we handle output).
    $robocopyArgs = @(
        $LocalKnowledge,
        $CloudDrivePath,
        "/MIR", "/R:3", "/W:2", "/MT:8", "/NFL", "/NDL", "/NJH", "/NJS"
    )

    Write-Log "Syncing files..." "Cyan"
    
    # Execute Robocopy
    $p = Start-Process -FilePath "robocopy.exe" -ArgumentList $robocopyArgs -Wait -PassThru -NoNewWindow
    
    # Robocopy exit codes:
    # 0 = No changes
    # 1 = Successful copy
    # 2 = Extra files detected (not present in source)
    # 3 = Successful copy + Extra files
    # >= 8 = Failures
    
    if ($p.ExitCode -lt 8) {
        Write-Log "✅ Backup successful!" "Green"
    }
    else {
        Write-Log "❌ Backup failed with error code: $($p.ExitCode)" "Red"
    }
}

function Sync-From-Cloud {
    Write-Log "Preparing to sync Cloud -> Local (Restore)..." "Cyan"
    
    if (-not (Test-Path $CloudDrivePath)) {
        Write-Log "Cloud backup not found at: $CloudDrivePath" "Red"
        return
    }

    Write-Log "⚠️  WARNING: This will replace local files with cloud version!" "Yellow"
    $confirm = Read-Host "Are you sure? (y/N)"
    if ($confirm -ne 'y') { return }

    $robocopyArgs = @(
        $CloudDrivePath,
        $LocalKnowledge,
        "/MIR", "/R:3", "/W:2", "/MT:8", "/NFL", "/NDL", "/NJH", "/NJS"
    )

    Write-Log "Restoring files from cloud..." "Cyan"
    $p = Start-Process -FilePath "robocopy.exe" -ArgumentList $robocopyArgs -Wait -PassThru -NoNewWindow
    
    if ($p.ExitCode -lt 8) {
        Write-Log "✅ Restore successful!" "Green"
    }
    else {
        Write-Log "❌ Restore failed!" "Red"
    }
}

# Main Interaction
if ($args[0] -eq "auto-backup") {
    Sync-To-Cloud
    exit
}

Write-Host "============================" -ForegroundColor Blue
Write-Host "☁️  York Knowledge Sync" -ForegroundColor Blue
Write-Host "============================" -ForegroundColor Blue
Write-Host "Local: $LocalKnowledge"
Write-Host "Cloud: $CloudDrivePath"
Write-Host ""
Write-Host "1. Backup (Local -> Cloud)" -ForegroundColor Green
Write-Host "2. Restore (Cloud -> Local)" -ForegroundColor Red
Write-Host "Q. Quit"
Write-Host ""

$choice = Read-Host "Select option"

switch ($choice) {
    '1' { Sync-To-Cloud }
    '2' { Sync-From-Cloud }
    'q' { exit }
    default { Write-Host "Invalid option" }
}
