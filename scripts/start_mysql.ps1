$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$mysqld = "C:\Program Files\MySQL\MySQL Server 8.4\bin\mysqld.exe"
$defaultsFile = Join-Path $repoRoot "database\my.ini"

if (-not (Test-Path $mysqld)) {
    throw "mysqld.exe not found: $mysqld"
}

if (-not (Test-Path $defaultsFile)) {
    throw "MySQL config not found: $defaultsFile"
}

$existing = Get-Process -Name mysqld -ErrorAction SilentlyContinue |
    Where-Object { $_.Path -eq $mysqld }

if ($existing) {
    Write-Host "MySQL is already running. PID: $($existing.Id -join ', ')"
    exit 0
}

Start-Process -FilePath $mysqld `
    -ArgumentList "--defaults-file=`"$defaultsFile`"" `
    -WindowStyle Hidden

Start-Sleep -Seconds 3
Write-Host "MySQL start command issued."
