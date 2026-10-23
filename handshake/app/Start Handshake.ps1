$ErrorActionPreference = 'Stop'
$taskAppRoot = $PSScriptRoot
$taskPort = if ($env:HANDSHAKE_PORT) { [int]$env:HANDSHAKE_PORT } else { 8800 }
$taskUrl = "http://127.0.0.1:$taskPort"
try {
    $taskExisting = Invoke-WebRequest -Uri "$taskUrl/api/session" -TimeoutSec 2
    if ($taskExisting.Headers.Server -notmatch 'Handshake/') { throw 'Port is occupied by another service.' }
    Write-Output "FOM is already running: $taskUrl/#home"
    exit 0
} catch {
    if ($_.Exception.Message -eq 'Port is occupied by another service.') { throw }
}
$taskPython = (Get-Command python -ErrorAction Stop).Source
$taskServer = Join-Path $taskAppRoot 'server.py'
$taskLogs = Join-Path $taskAppRoot 'data'
New-Item -ItemType Directory -Path $taskLogs -Force | Out-Null
$taskProcess = Start-Process -FilePath $taskPython -ArgumentList ('"' + $taskServer + '"') -WorkingDirectory $taskAppRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $taskLogs 'server-output.log') -RedirectStandardError (Join-Path $taskLogs 'server-error.log') -PassThru
Set-Content -LiteralPath (Join-Path $taskLogs 'server.pid') -Value $taskProcess.Id
for ($taskAttempt = 0; $taskAttempt -lt 20; $taskAttempt++) {
    try {
        $taskReady = Invoke-WebRequest -Uri "$taskUrl/api/session" -TimeoutSec 1
        if ($taskReady.StatusCode -eq 200 -and $taskReady.Headers.Server -match 'Handshake/') {
            Write-Output "FOM is running: $taskUrl/#home"
            exit 0
        }
    } catch { Start-Sleep -Milliseconds 200 }
}
throw "FOM did not become ready. See $taskLogs/server-error.log."
