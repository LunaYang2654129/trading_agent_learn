$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$mysql = "C:\Program Files\MySQL\MySQL Server 8.4\bin\mysql.exe"
$schema = Join-Path $repoRoot "database\schema.sql"
$seed = Join-Path $repoRoot "database\seed.sql"

if (-not (Test-Path $mysql)) {
    throw "mysql.exe not found: $mysql"
}

Get-Content $schema | & $mysql -u root --protocol=tcp --host=127.0.0.1 --port=3306
Get-Content $seed | & $mysql -u root --protocol=tcp --host=127.0.0.1 --port=3306

Write-Host "Database schema and seed data initialized."
