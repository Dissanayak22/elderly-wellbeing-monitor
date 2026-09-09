param(
    [switch]$ManagedOnly
)

Set-StrictMode -Version 2.0
$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $projectRoot "scripts\service-common.ps1")

$runtimeDirectory = Join-Path $projectRoot ".runtime"
$statePath = Join-Path $runtimeDirectory "services.json"
$pythonExecutable = Join-Path $projectRoot ".venv\Scripts\python.exe"
$mutex = $null
$mutexAcquired = $false
$hadFailure = $false
$stoppedIds = @()

function Stop-ManagedRecord {
    param(
        [AllowNull()]
        [object]$Record,
        [Parameter(Mandatory = $true)]
        [ValidateSet("backend", "frontend")]
        [string]$Kind,
        [Parameter(Mandatory = $true)]
        [string]$ExpectedExecutable,
        [Parameter(Mandatory = $true)]
        [int]$Port
    )

    if ($null -eq $Record) {
        return
    }

    if (-not (Test-EwmManagedRecord `
        -Record $Record `
        -ExpectedExecutable $ExpectedExecutable `
        -ExpectedPort $Port)) {
        Write-Warning "Ignoring stale or mismatched $Kind PID state."
        return
    }

    $processId = [int]$Record.pid
    Write-Host "Stopping managed $Kind (PID $processId)..."
    Stop-EwmProcessTree -ProcessId $processId -Kind $Kind
    $script:stoppedIds += $processId
}

function Stop-VerifiedPortService {
    param(
        [Parameter(Mandatory = $true)]
        [ValidateSet("backend", "frontend")]
        [string]$Kind,
        [Parameter(Mandatory = $true)]
        [int]$Port
    )

    $listenerIds = @(Get-EwmListeningProcessIds -Port $Port)
    if ($listenerIds.Count -eq 0) {
        return
    }

    $isOurService = if ($Kind -eq "backend") {
        Test-EwmBackendEndpoint -Uri "http://127.0.0.1:$Port/api/health"
    }
    else {
        Test-EwmFrontendEndpoint -Uri "http://127.0.0.1:$Port"
    }
    if (-not $isOurService) {
        Write-Warning "Port $Port is in use by another application; it was not stopped."
        return
    }

    foreach ($listenerId in $listenerIds) {
        if ($script:stoppedIds -contains $listenerId) {
            continue
        }
        Write-Host "Stopping verified legacy $Kind on port $Port (PID $listenerId)..."
        Stop-EwmProcessTree -ProcessId $listenerId -Kind $Kind
        $script:stoppedIds += $listenerId
    }
}

try {
    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host " Elderly Wellbeing Monitor - Safe Service Stop" -ForegroundColor Cyan
    Write-Host "============================================================" -ForegroundColor Cyan

    $mutex = New-Object System.Threading.Mutex(
        $false,
        "Local\ElderlyWellbeingMonitorLauncher"
    )
    try {
        $mutexAcquired = $mutex.WaitOne([TimeSpan]::FromSeconds(5))
    }
    catch [System.Threading.AbandonedMutexException] {
        $mutexAcquired = $true
    }
    if (-not $mutexAcquired) {
        throw "A start or stop operation is already running. Wait a moment and try again."
    }

    $nodeCommand = Get-Command node.exe -ErrorAction SilentlyContinue
    $nodeExecutable = if ($null -ne $nodeCommand) {
        [string]$nodeCommand.Source
    }
    else {
        "node.exe"
    }

    $state = Read-EwmState -StatePath $statePath
    Stop-ManagedRecord `
        -Record (Get-EwmStateRecord -State $state -Kind "frontend") `
        -Kind "frontend" `
        -ExpectedExecutable $nodeExecutable `
        -Port 5173
    Stop-ManagedRecord `
        -Record (Get-EwmStateRecord -State $state -Kind "backend") `
        -Kind "backend" `
        -ExpectedExecutable $pythonExecutable `
        -Port 8000

    if (-not $ManagedOnly) {
        # Compatibility cleanup for instances created by the old scripts.
        # Each endpoint is verified as this project before its exact PID is stopped.
        for ($attempt = 0; $attempt -lt 4; $attempt++) {
            Stop-VerifiedPortService -Kind "backend" -Port 8000
            foreach ($frontendPort in @(5173, 5174, 5175, 8080)) {
                Stop-VerifiedPortService -Kind "frontend" -Port $frontendPort
            }
            Start-Sleep -Milliseconds 400
        }
    }

    $remainingProjectServices = @()
    if (Test-EwmBackendEndpoint -Uri "http://127.0.0.1:8000/api/health") {
        $remainingProjectServices += "backend:8000"
    }
    foreach ($frontendPort in @(5173, 5174, 5175, 8080)) {
        if (Test-EwmFrontendEndpoint -Uri "http://127.0.0.1:$frontendPort") {
            $remainingProjectServices += "frontend:$frontendPort"
        }
    }

    if ($remainingProjectServices.Count -gt 0) {
        $hadFailure = $true
        Write-Warning (
            "Some verified project services are still running: " +
            ($remainingProjectServices -join ", ")
        )
    }
    else {
        if (Test-Path -LiteralPath $statePath -PathType Leaf) {
            Remove-Item -LiteralPath $statePath -Force
        }
        Write-Host "[OK] Project services are stopped." -ForegroundColor Green
        Write-Host "Other Python and Node.js applications were not touched." -ForegroundColor DarkGray
    }
}
catch {
    $hadFailure = $true
    Write-Host "[FAILED] $($_.Exception.Message)" -ForegroundColor Red
}
finally {
    if ($mutexAcquired -and $null -ne $mutex) {
        try {
            $mutex.ReleaseMutex()
        }
        catch {
            # Nothing else is required during shutdown.
        }
    }
    if ($null -ne $mutex) {
        $mutex.Dispose()
    }
}

if ($hadFailure) {
    exit 1
}
exit 0
