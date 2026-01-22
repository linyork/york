###############################################################################
# LanceDB Management Tool (Windows PowerShell)
# Purpose: Manage vector database (backup, restore, reset)
###############################################################################

param(
    [Parameter(Position = 0)]
    [ValidateSet('backup', 'reset', 'help')]
    [string]$Command = 'help'
)

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

if (-not $env:YORK_KNOWLEDGE_ROOT) {
    $env:YORK_KNOWLEDGE_ROOT = Join-Path $ScriptDir "york-knowledge"
}

$DB_PATH = Join-Path $env:YORK_KNOWLEDGE_ROOT "lancedb"
$BACKUP_DIR = Join-Path $env:YORK_KNOWLEDGE_ROOT "backups"

# Ensure backup directory exists
if (-not (Test-Path $BACKUP_DIR)) {
    New-Item -ItemType Directory -Path $BACKUP_DIR -Force | Out-Null
}

function Show-Help {
    Write-Host "Usage: .\ops_db.ps1 [command]" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Commands:" -ForegroundColor Yellow
    Write-Host "  backup    Backup vector database"
    Write-Host "  reset     Reset (delete) vector database"
    Write-Host "  help      Show this help"
    Write-Host ""
}

function Backup-Database {
    if (-not (Test-Path $DB_PATH)) {
        Write-Host "❌ Database does not exist: $DB_PATH" -ForegroundColor Red
        exit 1
    }
    
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $backupFile = Join-Path $BACKUP_DIR "lancedb_$timestamp.zip"
    
    Write-Host "📦 Backing up database..." -ForegroundColor Cyan
    Compress-Archive -Path $DB_PATH -DestinationPath $backupFile -Force
    
    Write-Host "✅ Backup completed: $backupFile" -ForegroundColor Green
}

function Reset-Database {
    if (-not (Test-Path $DB_PATH)) {
        Write-Host "⚠️  Database does not exist, no need to reset" -ForegroundColor Yellow
        return
    }
    
    Write-Host "⚠️  WARNING: This will delete all vector data!" -ForegroundColor Yellow
    $confirm = Read-Host "Are you sure you want to continue? (y/N)"
    
    if ($confirm -ne 'y' -and $confirm -ne 'Y') {
        Write-Host "Cancelled" -ForegroundColor Yellow
        exit 0
    }
    
    # Auto backup first
    Backup-Database
    
    Write-Host "🗑️  Deleting database..." -ForegroundColor Yellow
    Remove-Item -Path $DB_PATH -Recurse -Force
    
    Write-Host "✅ Database has been reset" -ForegroundColor Green
}

# Execute command
switch ($Command) {
    'backup' {
        Backup-Database
    }
    'reset' {
        Reset-Database
    }
    default {
        Show-Help
    }
}
