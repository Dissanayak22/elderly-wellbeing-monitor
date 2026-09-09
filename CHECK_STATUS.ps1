param(
    [switch]$Deep,
    [switch]$ShowLogs
)

Set-StrictMode -Version 2.0
$ErrorActionPreference = "Continue"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $projectRoot "scripts\service-common.ps1")

$runtimeDirectory = Join-Path $projectRoot ".runtime"
$statePath = Join-Path $runtimeDirectory "services.json"
$logDirectory = Join-Path $runtimeDirectory "logs"
$pythonExecutable = Join-Path $projectRoot ".venv\Scripts\python.exe"
$nodeCommand = Get-Command node.exe -ErrorAction SilentlyContinue
$nodeExecutable = if ($null -ne $nodeCommand) { [string]$nodeCommand.Source } else { $null }
$state = Read-EwmState -StatePath $statePath
$rows = @()
$overallHealthy = $true

function Get-ProcessDescription {
    param([int[]]$ProcessIds)

    if ($ProcessIds.Count -eq 0) {
        return "-"
    }
    $descriptions = @()
    foreach ($processId in $ProcessIds) {
        $info = Get-EwmProcessInfo -ProcessId $processId
        if ($null -eq $info) {
            $descriptions += "PID $processId"
        }
        else {
            $descriptions += "PID $processId ($($info.path))"
        }
    }
    return $descriptions -join "; "
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " Elderly Wellbeing Monitor - Local Service Status" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

$backendProcessIds = @(Get-EwmListeningProcessIds -Port 8000)
$backendEndpointHealthy = Test-EwmBackendEndpoint -Uri "http://127.0.0.1:8000/api/health"
$backendRecord = Get-EwmStateRecord -State $state -Kind "backend"
$backendManaged = $false
if (Test-Path -LiteralPath $pythonExecutable -PathType Leaf) {
    $backendManaged = (
        (Test-EwmManagedRecord `
            -Record $backendRecord `
            -ExpectedExecutable $pythonExecutable `
            -ExpectedPort 8000) -and
        $backendEndpointHealthy
    )
}

$backendStatus = if ($backendManaged) {
    "READY (managed)"
}
elseif ($backendEndpointHealthy) {
    $overallHealthy = $false
    "WARNING: project API is untracked or uses the wrong Python"
}
elseif ($backendProcessIds.Count -gt 0) {
    $overallHealthy = $false
    "BLOCKED: another application owns port 8000"
}
else {
    $overallHealthy = $false
    "STOPPED"
}
$rows += [pscustomobject]@{
    Service = "Backend"
    Url = "http://127.0.0.1:8000/api/health"
    Status = $backendStatus
    Process = Get-ProcessDescription -ProcessIds $backendProcessIds
}

$frontendProcessIds = @(Get-EwmListeningProcessIds -Port 5173)
$frontendEndpointHealthy = Test-EwmFrontendEndpoint -Uri "http://127.0.0.1:5173"
$frontendRecord = Get-EwmStateRecord -State $state -Kind "frontend"
$frontendManaged = $false
if (-not [string]::IsNullOrWhiteSpace($nodeExecutable)) {
    $frontendManaged = (
        (Test-EwmManagedRecord `
            -Record $frontendRecord `
            -ExpectedExecutable $nodeExecutable `
            -ExpectedPort 5173) -and
        $frontendEndpointHealthy
    )
}

$frontendStatus = if ($frontendManaged) {
    "READY (managed)"
}
elseif ($frontendEndpointHealthy) {
    $overallHealthy = $false
    "WARNING: project UI is untracked"
}
elseif ($frontendProcessIds.Count -gt 0) {
    $overallHealthy = $false
    "BLOCKED: another application owns port 5173"
}
else {
    $overallHealthy = $false
    "STOPPED"
}
$rows += [pscustomobject]@{
    Service = "Frontend"
    Url = "http://127.0.0.1:5173"
    Status = $frontendStatus
    Process = Get-ProcessDescription -ProcessIds $frontendProcessIds
}

foreach ($legacyPort in @(5174, 5175, 8080)) {
    if (Test-EwmFrontendEndpoint -Uri "http://127.0.0.1:$legacyPort") {
        $overallHealthy = $false
        $legacyIds = @(Get-EwmListeningProcessIds -Port $legacyPort)
        $rows += [pscustomobject]@{
            Service = "Legacy UI"
            Url = "http://127.0.0.1:$legacyPort"
            Status = "STALE: run STOP_SERVICES.bat"
            Process = Get-ProcessDescription -ProcessIds $legacyIds
        }
    }
}

$rows | Format-Table -AutoSize -Wrap

Write-Host "Preflight:" -ForegroundColor Cyan
if (Test-Path -LiteralPath $pythonExecutable -PathType Leaf) {
    Write-Host "  [OK] Root Python environment: $pythonExecutable" -ForegroundColor Green
}
else {
    $overallHealthy = $false
    Write-Host "  [MISSING] Root Python environment: $pythonExecutable" -ForegroundColor Red
}

if ($null -ne $nodeCommand) {
    Write-Host "  [OK] Node.js: $nodeExecutable" -ForegroundColor Green
}
else {
    $overallHealthy = $false
    Write-Host "  [MISSING] Node.js is not on PATH" -ForegroundColor Red
}

$viteScript = Join-Path $projectRoot "frontend\node_modules\vite\bin\vite.js"
if (Test-Path -LiteralPath $viteScript -PathType Leaf) {
    Write-Host "  [OK] Frontend dependencies are installed" -ForegroundColor Green
}
else {
    $overallHealthy = $false
    Write-Host "  [MISSING] Run: npm.cmd --prefix frontend ci" -ForegroundColor Red
}

if ($Deep -and (Test-Path -LiteralPath $pythonExecutable -PathType Leaf)) {
    Write-Host ""
    Write-Host "Deep dependency and local model-cache check:" -ForegroundColor Cyan
    & $pythonExecutable -c (
        "import sys; " +
        "import fastapi, uvicorn, sqlalchemy, cv2, torch, torchvision, transformers; " +
        "from huggingface_hub import snapshot_download; " +
        "path=snapshot_download('dima806/facial_emotions_image_detection', local_files_only=True); " +
        "print('  [OK] Backend/AI imports'); " +
        "print('  [OK] Local model snapshot: ' + path)"
    )
    if ($LASTEXITCODE -ne 0) {
        $overallHealthy = $false
        Write-Host "  [FAILED] AI dependencies or local model cache are incomplete." -ForegroundColor Red
        Write-Host "  Run: npm run model:check" -ForegroundColor Yellow
    }
}

if ($ShowLogs) {
    Write-Host ""
    Show-EwmLogTail -Paths @(
        (Join-Path $logDirectory "backend.error.log"),
        (Join-Path $logDirectory "backend.log"),
        (Join-Path $logDirectory "frontend.error.log"),
        (Join-Path $logDirectory "frontend.log")
    ) -Lines 40
}

Write-Host ""
if ($overallHealthy) {
    Write-Host "[OK] Both services are verified on the canonical ports." -ForegroundColor Green
    exit 0
}

Write-Host "[ACTION] Run STOP_SERVICES.bat once, then START_ALL.bat." -ForegroundColor Yellow
exit 1
