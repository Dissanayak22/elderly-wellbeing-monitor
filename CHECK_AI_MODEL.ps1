param(
    [switch]$AllowDownload
)

Set-StrictMode -Version 2.0
$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonExecutable = Join-Path $projectRoot ".venv\Scripts\python.exe"
$modelName = "dima806/facial_emotions_image_detection"

try {
    if (-not (Test-Path -LiteralPath $pythonExecutable -PathType Leaf)) {
        throw "Root Python environment not found: $pythonExecutable"
    }

    Write-Host "Checking facial-expression model: $modelName" -ForegroundColor Cyan
    if ($AllowDownload) {
        Write-Host "Download is explicitly enabled for this one-time check." -ForegroundColor Yellow
        $localOnly = "False"
    }
    else {
        Write-Host "Offline cache-only mode; no network download will be attempted." -ForegroundColor DarkGray
        $localOnly = "True"
    }

    & $pythonExecutable -c (
        "from huggingface_hub import snapshot_download; " +
        "from transformers import pipeline; " +
        "repo='$modelName'; " +
        "path=snapshot_download(repo, local_files_only=$localOnly); " +
        "pipeline('image-classification', model=path, device=-1); " +
        "print('Model cache and weights loaded successfully from: ' + path)"
    )
    if ($LASTEXITCODE -ne 0) {
        throw "The model cache/weight check failed with exit code $LASTEXITCODE."
    }

    Write-Host "[OK] The real model is available to the project environment." -ForegroundColor Green
    Write-Host "This validation process now exits; the backend loads its own model on the first prediction." -ForegroundColor DarkGray
    exit 0
}
catch {
    Write-Host "[FAILED] $($_.Exception.Message)" -ForegroundColor Red
    if (-not $AllowDownload) {
        Write-Host "For an intentional one-time download, run: npm run model:download" -ForegroundColor Yellow
    }
    exit 1
}
