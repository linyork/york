###############################################################################
# Docker Image Build Script for York (Windows PowerShell)
###############################################################################

$ErrorActionPreference = "Stop"

# Define image name
$IMAGE_NAME = "mcp/york"

# Change to script directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host "🔨 Building Docker Image: $IMAGE_NAME..." -ForegroundColor Cyan

# Check and clean up old containers using this image
$oldContainers = docker ps -a -q -f "ancestor=$IMAGE_NAME" 2>$null
if ($oldContainers) {
    Write-Host "Found containers using image, stopping and removing..." -ForegroundColor Yellow
    docker stop $oldContainers 2>$null | Out-Null
    docker rm $oldContainers 2>$null | Out-Null
}

# Check and remove old image
$oldImage = docker images -q $IMAGE_NAME 2>$null
if ($oldImage) {
    Write-Host "Removing old image..." -ForegroundColor Yellow
    docker rmi -f $IMAGE_NAME 2>$null | Out-Null
}

# Build the image
Write-Host "Building new image..." -ForegroundColor Green
docker build -t $IMAGE_NAME .

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Build completed successfully!" -ForegroundColor Green
}
else {
    Write-Host "❌ Build failed!" -ForegroundColor Red
    exit 1
}
