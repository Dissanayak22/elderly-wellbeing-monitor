param(
    [switch]$NoBrowser,
    [ValidateRange(10, 180)]
    [int]$BackendTimeoutSeconds = 60,
    [ValidateRange(10, 180)]
    [int]$FrontendTimeoutSeconds = 30
)

Set-StrictMode -Version 2.0
$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$commonScript = Join-Path $projectRoot "scripts\service-common.ps1"
. $commonScript

$backendPort = 8000
$frontendPort = 5173
$backendUrl = "http://127.0.0.1:$backendPort"
$frontendUrl = "http://127.0.0.1:$frontendPort"
$healthUrl = "$backendUrl/api/health"
$runtimeDirectory = Join-Path $projectRoot ".runtime"
$logDirectory = Join-Path $runtimeDirectory "logs"
$statePath = Join-Path $runtimeDirectory "services.json"
$pythonExecutable = Join-Path $projectRoot ".venv\Scripts\python.exe"
$frontendDirectory = Join-Path $projectRoot "frontend"
$viteRelativePath = "node_modules\vite\bin\vite.js"
$viteScript = Join-Path $frontendDirectory $viteRelativePath
$backendOutputLog = Join-Path $logDirectory "backend.log"
$backendErrorLog = Join-Path $logDirectory "backend.error.log"
$frontendOutputLog = Join-Path $logDirectory "frontend.log"
$frontendErrorLog = Join-Path $logDirectory "frontend.error.log"

$mutex = $null
$mutexAcquired = $false
$startedBackendRecord = $null
$startedFrontendRecord = $null
$backendRecord = $null
$frontendRecord = $null
$nodeExecutable = $null
$exitCode = 0

function Write-Step {
    param([string]$Message)
    Write-Host "[EWM] $Message" -ForegroundColor Cyan
}

function Assert-CommandSucceeded {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Description,
        [Parameter(Mandatory = $true)]
        [scriptblock]$Command
    )

    $previousPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $output = & $Command 2>&1
        $commandExitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousPreference
    }

    if ($commandExitCode -ne 0) {
        $details = ($output | ForEach-Object { [string]$_ }) -join [Environment]::NewLine
        throw "$Description failed with exit code $commandExitCode.$([Environment]::NewLine)$details"
    }
}

function Wait-BackendReady {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Record,
        [Parameter(Mandatory = $true)]
        [int]$TimeoutSeconds
    )

    $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
    while ([DateTime]::UtcNow -lt $deadline) {
        if ($null -eq (Get-EwmProcessInfo -ProcessId ([int]$Record.pid))) {
            return $false
        }
        if (
            (Test-EwmBackendEndpoint -Uri $healthUrl) -and
            (Test-EwmManagedRecord `
                -Record $Record `
                -ExpectedExecutable $pythonExecutable `
                -ExpectedPort $backendPort)
        ) {
            return $true
        }
        Start-Sleep -Milliseconds 500
    }
    return $false
}

function Wait-FrontendReady {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Record,
        [Parameter(Mandatory = $true)]
        [int]$TimeoutSeconds
    )

    $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
    while ([DateTime]::UtcNow -lt $deadline) {
        if ($null -eq (Get-EwmProcessInfo -ProcessId ([int]$Record.pid))) {
            return $false
        }
        if (
            (Test-EwmFrontendEndpoint -Uri $frontendUrl) -and
            (Test-EwmManagedRecord `
                -Record $Record `
                -ExpectedExecutable $nodeExecutable `
                -ExpectedPort $frontendPort)
        ) {
            return $true
        }
        Start-Sleep -Milliseconds 350
    }
    return $false
}

function Stop-RecognizedListener {
    param(
        [Parameter(Mandatory = $true)]
        [ValidateSet("backend", "frontend")]
        [string]$Kind,
        [Parameter(Mandatory = $true)]
        [int]$Port,
        [switch]$RequiredToBeOurs
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
        if ($RequiredToBeOurs) {
            $pidText = ($listenerIds -join ", ")
            throw "Port $Port is occupied by another application (PID: $pidText). Close it and run START_ALL.bat again."
        }
        return
    }

    Write-Warning "Stopping an older untracked $Kind instance on port $Port."
    foreach ($listenerId in $listenerIds) {
        Stop-EwmProcessTree -ProcessId $listenerId -Kind $Kind
    }

    # A legacy Uvicorn reload parent can briefly replace its child. Stop only
    # listeners that still identify as this project, never arbitrary processes.
    for ($attempt = 0; $attempt -lt 4; $attempt++) {
        if (Wait-EwmPortFree -Port $Port -TimeoutSeconds 2) {
            return
        }
        $stillOurs = if ($Kind -eq "backend") {
            Test-EwmBackendEndpoint -Uri "http://127.0.0.1:$Port/api/health"
        }
        else {
            Test-EwmFrontendEndpoint -Uri "http://127.0.0.1:$Port"
        }
        if (-not $stillOurs) {
            break
        }
        foreach ($replacementId in @(Get-EwmListeningProcessIds -Port $Port)) {
            Stop-EwmProcessTree -ProcessId $replacementId -Kind $Kind
        }
    }

    if (-not (Test-EwmPortFree -Port $Port)) {
        throw "Could not release port $Port safely. Run CHECK_STATUS.ps1 for details."
    }
}

function Save-CurrentState {
    Write-EwmState `
        -StatePath $statePath `
        -Backend $backendRecord `
        -Frontend $frontendRecord `
        -ProjectRoot $projectRoot
}

try {
    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host " Elderly Wellbeing Monitor - Reliable Local Startup" -ForegroundColor Cyan
    Write-Host "============================================================" -ForegroundColor Cyan

    $mutex = New-Object System.Threading.Mutex(
        $false,
        "Local\ElderlyWellbeingMonitorLauncher"
    )
    try {
        $mutexAcquired = $mutex.WaitOne([TimeSpan]::FromSeconds(2))
    }
    catch [System.Threading.AbandonedMutexException] {
        $mutexAcquired = $true
    }
    if (-not $mutexAcquired) {
        throw "Another start or stop operation is already running. Wait a moment and try again."
    }

    Set-Location -LiteralPath $projectRoot
    New-Item -ItemType Directory -Path $logDirectory -Force | Out-Null

    Write-Step "Checking the canonical Python environment..."
    if (-not (Test-Path -LiteralPath $pythonExecutable -PathType Leaf)) {
        throw (
            "Python environment not found at $pythonExecutable`n" +
            "Create it from the project root:`n" +
            "  py -3.12 -m venv .venv`n" +
            "  .\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt"
        )
    }
    Assert-CommandSucceeded -Description "Backend dependency check" -Command {
        & $pythonExecutable -c (
            "import sys; " +
            "assert sys.prefix != sys.base_prefix, 'not running inside a virtual environment'; " +
            "import fastapi, uvicorn, sqlalchemy, pydantic, cv2, torch, torchvision, transformers; " +
            "print('backend dependencies OK')"
        )
    }

    Write-Step "Checking Node.js and frontend dependencies..."
    $nodeCommand = Get-Command node.exe -ErrorAction SilentlyContinue
    if ($null -eq $nodeCommand) {
        throw "Node.js was not found on PATH. Install Node.js 18 or newer, then reopen the terminal."
    }
    $nodeExecutable = [string]$nodeCommand.Source
    if (-not (Test-Path -LiteralPath (Join-Path $frontendDirectory "package.json") -PathType Leaf)) {
        throw "Frontend package.json was not found in $frontendDirectory."
    }
    if (-not (Test-Path -LiteralPath $viteScript -PathType Leaf)) {
        throw (
            "Frontend dependencies are missing.`n" +
            "Run from the project root: npm.cmd --prefix frontend ci"
        )
    }
    Assert-CommandSucceeded -Description "Node.js check" -Command {
        & $nodeExecutable --version
    }
    Assert-CommandSucceeded -Description "Vite dependency check" -Command {
        Push-Location -LiteralPath $frontendDirectory
        try {
            & $nodeExecutable $viteRelativePath --version
        }
        finally {
            Pop-Location
        }
    }

    $existingState = Read-EwmState -StatePath $statePath
    $oldBackendRecord = Get-EwmStateRecord -State $existingState -Kind "backend"
    $oldFrontendRecord = Get-EwmStateRecord -State $existingState -Kind "frontend"

    if (
        (Test-EwmManagedRecord `
            -Record $oldBackendRecord `
            -ExpectedExecutable $pythonExecutable `
            -ExpectedPort $backendPort) -and
        (Test-EwmBackendEndpoint -Uri $healthUrl)
    ) {
        $backendRecord = $oldBackendRecord
        Write-Step "Backend is already healthy and managed (PID $($backendRecord.pid))."
    }
    else {
        Stop-RecognizedListener -Kind "backend" -Port $backendPort -RequiredToBeOurs
    }

    if (
        (Test-EwmManagedRecord `
            -Record $oldFrontendRecord `
            -ExpectedExecutable $nodeExecutable `
            -ExpectedPort $frontendPort) -and
        (Test-EwmFrontendEndpoint -Uri $frontendUrl)
    ) {
        $frontendRecord = $oldFrontendRecord
        Write-Step "Frontend is already healthy and managed (PID $($frontendRecord.pid))."
    }
    else {
        Stop-RecognizedListener -Kind "frontend" -Port $frontendPort -RequiredToBeOurs
    }

    # Remove only verified old copies of this frontend that Vite previously
    # moved to fallback ports. Other applications on these ports are untouched.
    foreach ($legacyFrontendPort in @(5174, 5175, 8080)) {
        Stop-RecognizedListener -Kind "frontend" -Port $legacyFrontendPort
    }

    if ($null -eq $backendRecord) {
        if (-not (Test-EwmPortFree -Port $backendPort)) {
            throw "Backend port $backendPort is still occupied. Run CHECK_STATUS.ps1 for details."
        }

        Write-Step "Starting backend with the project virtual environment..."
        Set-Content -LiteralPath $backendOutputLog -Value "" -Encoding UTF8
        Set-Content -LiteralPath $backendErrorLog -Value "" -Encoding UTF8
        $env:PYTHONPATH = $projectRoot
        $env:PYTHONUNBUFFERED = "1"
        $backendProcess = Start-Process `
            -FilePath $pythonExecutable `
            -ArgumentList @(
                "-m",
                "uvicorn",
                "backend.app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                [string]$backendPort
            ) `
            -WorkingDirectory $projectRoot `
            -RedirectStandardOutput $backendOutputLog `
            -RedirectStandardError $backendErrorLog `
            -WindowStyle Hidden `
            -PassThru
        $backendRecord = New-EwmProcessRecord `
            -Process $backendProcess `
            -Executable $pythonExecutable `
            -Port $backendPort
        $startedBackendRecord = $backendRecord
        Save-CurrentState

        if (-not (Wait-BackendReady -Record $backendRecord -TimeoutSeconds $BackendTimeoutSeconds)) {
            Show-EwmLogTail -Paths @($backendErrorLog, $backendOutputLog)
            throw "Backend did not become healthy within $BackendTimeoutSeconds seconds."
        }
        Write-Host "[OK] Backend ready: $healthUrl" -ForegroundColor Green
    }

    if ($null -eq $frontendRecord) {
        if (-not (Test-EwmPortFree -Port $frontendPort)) {
            throw "Frontend port $frontendPort is still occupied. Run CHECK_STATUS.ps1 for details."
        }

        Write-Step "Starting frontend on the strict port $frontendPort..."
        Set-Content -LiteralPath $frontendOutputLog -Value "" -Encoding UTF8
        Set-Content -LiteralPath $frontendErrorLog -Value "" -Encoding UTF8
        $frontendProcess = Start-Process `
            -FilePath $nodeExecutable `
            -ArgumentList @(
                $viteRelativePath,
                "--host",
                "127.0.0.1",
                "--port",
                [string]$frontendPort,
                "--strictPort"
            ) `
            -WorkingDirectory $frontendDirectory `
            -RedirectStandardOutput $frontendOutputLog `
            -RedirectStandardError $frontendErrorLog `
            -WindowStyle Hidden `
            -PassThru
        $frontendRecord = New-EwmProcessRecord `
            -Process $frontendProcess `
            -Executable $nodeExecutable `
            -Port $frontendPort
        $startedFrontendRecord = $frontendRecord
        Save-CurrentState

        if (-not (Wait-FrontendReady -Record $frontendRecord -TimeoutSeconds $FrontendTimeoutSeconds)) {
            Show-EwmLogTail -Paths @($frontendErrorLog, $frontendOutputLog)
            throw "Frontend did not become healthy within $FrontendTimeoutSeconds seconds."
        }
        Write-Host "[OK] Frontend ready: $frontendUrl" -ForegroundColor Green
    }

    Save-CurrentState
    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Green
    Write-Host " Both services are verified and ready" -ForegroundColor Green
    Write-Host "============================================================" -ForegroundColor Green
    Write-Host "Frontend: $frontendUrl"
    Write-Host "API docs: $backendUrl/docs"
    Write-Host "Health:   $healthUrl"
    Write-Host "Logs:     $logDirectory"
    Write-Host "Stop:     STOP_SERVICES.bat"
    Write-Host "Status:   npm run status"
    Write-Host "AI check: npm run model:check (optional, cache-only)"

    if (-not $NoBrowser) {
        try {
            Start-Process $frontendUrl | Out-Null
        }
        catch {
            Write-Warning "Could not open the browser automatically. Open $frontendUrl manually."
        }
    }
}
catch {
    $exitCode = 1
    Write-Host ""
    Write-Host "[FAILED] $($_.Exception.Message)" -ForegroundColor Red

    if ($null -ne $startedFrontendRecord) {
        try {
            Stop-EwmProcessTree -ProcessId ([int]$startedFrontendRecord.pid) -Kind "frontend"
        }
        catch {
            Write-Warning "Could not clean up the failed frontend process."
        }
        $frontendRecord = $null
    }
    if ($null -ne $startedBackendRecord) {
        try {
            Stop-EwmProcessTree -ProcessId ([int]$startedBackendRecord.pid) -Kind "backend"
        }
        catch {
            Write-Warning "Could not clean up the failed backend process."
        }
        $backendRecord = $null
    }

    try {
        Write-EwmState `
            -StatePath $statePath `
            -Backend $backendRecord `
            -Frontend $frontendRecord `
            -ProjectRoot $projectRoot
    }
    catch {
        Write-Warning "Could not update runtime state after the startup failure."
    }
    Show-EwmLogTail -Paths @(
        $backendErrorLog,
        $backendOutputLog,
        $frontendErrorLog,
        $frontendOutputLog
    )
    Write-Host "Run this for a diagnostic summary:" -ForegroundColor Yellow
    Write-Host "  powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\CHECK_STATUS.ps1"
}
finally {
    if ($mutexAcquired -and $null -ne $mutex) {
        try {
            $mutex.ReleaseMutex()
        }
        catch {
            # Nothing else is required during launcher shutdown.
        }
    }
    if ($null -ne $mutex) {
        $mutex.Dispose()
    }
}

exit $exitCode
