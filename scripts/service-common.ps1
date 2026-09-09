Set-StrictMode -Version 2.0

$script:EwmApplicationName = "Elderly Wellbeing Monitor"

function Get-EwmListeningProcessIds {
    param(
        [Parameter(Mandatory = $true)]
        [int]$Port
    )

    $processIds = @()
    $lines = & "$env:SystemRoot\System32\netstat.exe" -ano -p tcp 2>$null
    foreach ($line in $lines) {
        $match = [regex]::Match(
            [string]$line,
            '^\s*TCP\s+\S+:(?<port>\d+)\s+\S+\s+LISTENING\s+(?<pid>\d+)\s*$'
        )
        if ($match.Success -and [int]$match.Groups['port'].Value -eq $Port) {
            $processIds += [int]$match.Groups['pid'].Value
        }
    }

    return @($processIds | Sort-Object -Unique)
}

function Test-EwmPortFree {
    param(
        [Parameter(Mandatory = $true)]
        [int]$Port
    )

    return @(Get-EwmListeningProcessIds -Port $Port).Count -eq 0
}

function Test-EwmBackendEndpoint {
    param(
        [string]$Uri = "http://127.0.0.1:8000/api/health",
        [int]$TimeoutSeconds = 2
    )

    try {
        $response = Invoke-WebRequest `
            -UseBasicParsing `
            -Uri $Uri `
            -TimeoutSec $TimeoutSeconds `
            -ErrorAction Stop
        if ($response.StatusCode -ne 200) {
            return $false
        }
        $payload = $response.Content | ConvertFrom-Json -ErrorAction Stop
        return (
            [string]$payload.status -eq "ok" -and
            [string]$payload.app -eq $script:EwmApplicationName
        )
    }
    catch {
        return $false
    }
}

function Test-EwmFrontendEndpoint {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Uri,
        [int]$TimeoutSeconds = 2
    )

    try {
        $response = Invoke-WebRequest `
            -UseBasicParsing `
            -Uri $Uri `
            -TimeoutSec $TimeoutSeconds `
            -ErrorAction Stop
        return (
            $response.StatusCode -eq 200 -and
            [string]$response.Content -match '<title>\s*Elderly Wellbeing Monitor\s*</title>'
        )
    }
    catch {
        return $false
    }
}

function Get-EwmProcessInfo {
    param(
        [Parameter(Mandatory = $true)]
        [int]$ProcessId
    )

    try {
        $process = Get-Process -Id $ProcessId -ErrorAction Stop
        $processPath = $null
        try {
            $processPath = $process.Path
        }
        catch {
            $processPath = $null
        }

        return [pscustomobject]@{
            pid = [int]$process.Id
            name = [string]$process.ProcessName
            path = $processPath
            started_at_utc = $process.StartTime.ToUniversalTime().ToString("o")
        }
    }
    catch {
        return $null
    }
}

function Test-EwmSamePath {
    param(
        [AllowNull()]
        [string]$First,
        [AllowNull()]
        [string]$Second
    )

    if ([string]::IsNullOrWhiteSpace($First) -or [string]::IsNullOrWhiteSpace($Second)) {
        return $false
    }

    try {
        $firstFull = [System.IO.Path]::GetFullPath($First).TrimEnd('\')
        $secondFull = [System.IO.Path]::GetFullPath($Second).TrimEnd('\')
        return [string]::Equals(
            $firstFull,
            $secondFull,
            [System.StringComparison]::OrdinalIgnoreCase
        )
    }
    catch {
        return $false
    }
}

function Read-EwmState {
    param(
        [Parameter(Mandatory = $true)]
        [string]$StatePath
    )

    if (-not (Test-Path -LiteralPath $StatePath -PathType Leaf)) {
        return $null
    }

    try {
        return Get-Content -LiteralPath $StatePath -Raw -ErrorAction Stop |
            ConvertFrom-Json -ErrorAction Stop
    }
    catch {
        Write-Warning "Ignoring invalid runtime state: $StatePath"
        return $null
    }
}

function Get-EwmStateRecord {
    param(
        [AllowNull()]
        [object]$State,
        [Parameter(Mandatory = $true)]
        [ValidateSet("backend", "frontend")]
        [string]$Kind
    )

    if ($null -eq $State) {
        return $null
    }
    if ($State.PSObject.Properties.Name -notcontains $Kind) {
        return $null
    }
    return $State.$Kind
}

function Write-EwmState {
    param(
        [Parameter(Mandatory = $true)]
        [string]$StatePath,
        [AllowNull()]
        [object]$Backend,
        [AllowNull()]
        [object]$Frontend,
        [Parameter(Mandatory = $true)]
        [string]$ProjectRoot
    )

    $stateDirectory = Split-Path -Parent $StatePath
    if (-not (Test-Path -LiteralPath $stateDirectory -PathType Container)) {
        New-Item -ItemType Directory -Path $stateDirectory -Force | Out-Null
    }

    $payload = [ordered]@{
        version = 1
        project_root = $ProjectRoot
        updated_at_utc = [DateTime]::UtcNow.ToString("o")
        backend = $Backend
        frontend = $Frontend
    }

    $temporaryPath = "$StatePath.tmp"
    $payload | ConvertTo-Json -Depth 6 |
        Set-Content -LiteralPath $temporaryPath -Encoding UTF8
    Move-Item -LiteralPath $temporaryPath -Destination $StatePath -Force
}

function New-EwmProcessRecord {
    param(
        [Parameter(Mandatory = $true)]
        [System.Diagnostics.Process]$Process,
        [Parameter(Mandatory = $true)]
        [string]$Executable,
        [Parameter(Mandatory = $true)]
        [int]$Port
    )

    return [pscustomobject]@{
        pid = [int]$Process.Id
        executable = [System.IO.Path]::GetFullPath($Executable)
        started_at_utc = $Process.StartTime.ToUniversalTime().ToString("o")
        port = $Port
    }
}

function Test-EwmManagedRecord {
    param(
        [AllowNull()]
        [object]$Record,
        [Parameter(Mandatory = $true)]
        [string]$ExpectedExecutable,
        [Parameter(Mandatory = $true)]
        [int]$ExpectedPort
    )

    if ($null -eq $Record) {
        return $false
    }

    $requiredProperties = @("pid", "executable", "started_at_utc", "port")
    foreach ($propertyName in $requiredProperties) {
        if ($Record.PSObject.Properties.Name -notcontains $propertyName) {
            return $false
        }
    }

    if ([int]$Record.port -ne $ExpectedPort) {
        return $false
    }
    if (-not (Test-EwmSamePath -First ([string]$Record.executable) -Second $ExpectedExecutable)) {
        return $false
    }

    $processInfo = Get-EwmProcessInfo -ProcessId ([int]$Record.pid)
    if ($null -eq $processInfo) {
        return $false
    }
    if (-not (Test-EwmSamePath -First ([string]$processInfo.path) -Second $ExpectedExecutable)) {
        return $false
    }

    try {
        $recordedStart = [DateTime]::Parse([string]$Record.started_at_utc).ToUniversalTime()
        $actualStart = [DateTime]::Parse([string]$processInfo.started_at_utc).ToUniversalTime()
        if ([Math]::Abs(($recordedStart - $actualStart).TotalSeconds) -gt 2) {
            return $false
        }
    }
    catch {
        return $false
    }

    return @(Get-EwmListeningProcessIds -Port $ExpectedPort) -contains [int]$Record.pid
}

function Get-EwmTopServiceProcessId {
    param(
        [Parameter(Mandatory = $true)]
        [int]$ProcessId,
        [Parameter(Mandatory = $true)]
        [ValidateSet("backend", "frontend")]
        [string]$Kind
    )

    $topProcessId = $ProcessId
    try {
        for ($level = 0; $level -lt 4; $level++) {
            $current = Get-CimInstance `
                -ClassName Win32_Process `
                -Filter "ProcessId = $topProcessId" `
                -ErrorAction Stop
            if ($null -eq $current -or [int]$current.ParentProcessId -le 0) {
                break
            }

            $parentId = [int]$current.ParentProcessId
            $parent = Get-CimInstance `
                -ClassName Win32_Process `
                -Filter "ProcessId = $parentId" `
                -ErrorAction Stop
            if ($null -eq $parent) {
                break
            }

            $parentName = ([string]$parent.Name).ToLowerInvariant()
            $parentCommand = ([string]$parent.CommandLine).ToLowerInvariant()
            $isServiceParent = $false
            if ($Kind -eq "backend") {
                $isServiceParent = (
                    $parentName -in @("python.exe", "pythonw.exe", "uvicorn.exe") -and
                    $parentCommand -match 'uvicorn' -and
                    $parentCommand -match 'backend\.app\.main'
                )
            }
            else {
                $isServiceParent = (
                    $parentName -in @("node.exe", "cmd.exe") -and
                    $parentCommand -match '(vite|npm-cli\.js.+run.+dev)'
                )
            }

            if (-not $isServiceParent) {
                break
            }
            $topProcessId = $parentId
        }
    }
    catch {
        # Process command lines may be unavailable under restricted accounts.
        # The verified listener PID is still safe to stop directly.
    }

    return $topProcessId
}

function Stop-EwmProcessTree {
    param(
        [Parameter(Mandatory = $true)]
        [int]$ProcessId,
        [Parameter(Mandatory = $true)]
        [ValidateSet("backend", "frontend")]
        [string]$Kind
    )

    if ($ProcessId -eq $PID) {
        throw "Refusing to stop the current PowerShell process."
    }

    $processInfo = Get-EwmProcessInfo -ProcessId $ProcessId
    if ($null -eq $processInfo) {
        return
    }

    $topProcessId = Get-EwmTopServiceProcessId -ProcessId $ProcessId -Kind $Kind
    & "$env:SystemRoot\System32\taskkill.exe" /PID $topProcessId /T /F *> $null
    if ($LASTEXITCODE -ne 0) {
        Stop-Process -Id $ProcessId -Force -ErrorAction Stop
    }
}

function Wait-EwmPortFree {
    param(
        [Parameter(Mandatory = $true)]
        [int]$Port,
        [int]$TimeoutSeconds = 8
    )

    $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
    while ([DateTime]::UtcNow -lt $deadline) {
        if (Test-EwmPortFree -Port $Port) {
            return $true
        }
        Start-Sleep -Milliseconds 250
    }
    return Test-EwmPortFree -Port $Port
}

function Show-EwmLogTail {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Paths,
        [int]$Lines = 30
    )

    foreach ($path in $Paths) {
        if (Test-Path -LiteralPath $path -PathType Leaf) {
            Write-Host "----- $path -----" -ForegroundColor DarkGray
            Get-Content -LiteralPath $path -Tail $Lines -ErrorAction SilentlyContinue
        }
    }
}
