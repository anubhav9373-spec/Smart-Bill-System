$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$cloudflared = "C:\Program Files (x86)\cloudflared\cloudflared.exe"
$port = 5000
$stateDir = Join-Path $env:LOCALAPPDATA "SmartBill"
$stateFile = Join-Path $stateDir "smartbill-runtime.json"
$runId = [Guid]::NewGuid().ToString("N")
$tunnelOutput = Join-Path $env:TEMP "smartbill-cloudflared-$port-$runId.out.log"
$tunnelError = Join-Path $env:TEMP "smartbill-cloudflared-$port-$runId.err.log"

function Stop-TrackedProcess {
    param (
        [Parameter(Mandatory = $true)]
        [int] $ProcessId
    )

    $process = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
    if ($process) {
        Stop-Process -Id $ProcessId -Force -ErrorAction SilentlyContinue
    }
}

if (-not (Test-Path $stateDir)) {
    New-Item -ItemType Directory -Path $stateDir | Out-Null
}

if (Test-Path $stateFile) {
    try {
        $previousState = Get-Content -Path $stateFile -Raw | ConvertFrom-Json
        if ($previousState.cloudflaredPid) {
            Stop-TrackedProcess -ProcessId ([int] $previousState.cloudflaredPid)
        }
        if ($previousState.pythonPid) {
            Stop-TrackedProcess -ProcessId ([int] $previousState.pythonPid)
        }
    }
    catch {
    }
    finally {
        Remove-Item $stateFile -Force -ErrorAction SilentlyContinue
    }
}

if (-not (Test-Path $cloudflared)) {
    throw "cloudflared is not installed at $cloudflared."
}

$existing = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue |
    Select-Object -First 1
if ($existing) {
    Stop-Process -Id $existing.OwningProcess -Force
    Start-Sleep -Seconds 1
}

$handoffComplete = $false
$pythonProcess = $null
$tunnel = Start-Process -FilePath $cloudflared `
    -ArgumentList "tunnel --url http://127.0.0.1:$port --protocol http2 --no-autoupdate" `
    -RedirectStandardOutput $tunnelOutput `
    -RedirectStandardError $tunnelError `
    -PassThru `
    -WindowStyle Hidden

try {
    $publicUrl = $null
    for ($attempt = 0; $attempt -lt 60 -and -not $publicUrl; $attempt++) {
        Start-Sleep -Milliseconds 500
        $logFiles = @($tunnelOutput, $tunnelError) | Where-Object { Test-Path $_ }
        if ($logFiles) {
            $match = Select-String -Path $logFiles `
                -Pattern "https://[a-z0-9-]+\.trycloudflare\.com" `
                -AllMatches |
                Select-Object -Last 1
            if ($match) {
                $publicUrl = $match.Matches[0].Value
            }
        }
        if ($tunnel.HasExited) {
            throw "Cloudflare tunnel stopped before a public URL was created."
        }
    }

    if (-not $publicUrl) {
        throw "Timed out waiting for Cloudflare to create a public HTTPS URL."
    }

    Write-Host "SmartBill public URL: $publicUrl" -ForegroundColor Green
    Write-Host "Open this URL in the browser before creating a QR code."

    $pythonScript = @"
`$env:PORT = "$port"
`$env:SMARTBILL_PUBLIC_URL = "$publicUrl"
`$env:SMARTBILL_SECURE_COOKIES = "false"
Set-Location "$projectRoot"
& python app.py
"@
    $encodedCommand = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($pythonScript))
    $pythonProcess = Start-Process -FilePath powershell.exe `
        -ArgumentList @(
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-EncodedCommand",
            $encodedCommand
        ) `
        -WindowStyle Hidden `
        -PassThru

    $runtimeState = [pscustomobject]@{
        cloudflaredPid = $tunnel.Id
        pythonPid      = $pythonProcess.Id
        publicUrl      = $publicUrl
        port           = $port
        startedAt      = (Get-Date).ToString("o")
    }
    $runtimeState | ConvertTo-Json | Set-Content -Path $stateFile -Encoding UTF8

    Write-Host "SmartBill is running in the background." -ForegroundColor Green
    Write-Host "Cloudflared PID: $($tunnel.Id)"
    Write-Host "Python PID: $($pythonProcess.Id)"
    $handoffComplete = $true
}
finally {
    if (-not $handoffComplete) {
        if ($pythonProcess -and -not $pythonProcess.HasExited) {
            Stop-Process -Id $pythonProcess.Id -Force
        }

        if ($tunnel -and -not $tunnel.HasExited) {
            Stop-Process -Id $tunnel.Id -Force
        }
    }
}