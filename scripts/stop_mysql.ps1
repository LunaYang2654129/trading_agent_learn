$ErrorActionPreference = "Stop"

$mysqladmin = "C:\Program Files\MySQL\MySQL Server 8.4\bin\mysqladmin.exe"

if (-not (Test-Path $mysqladmin)) {
    throw "mysqladmin.exe not found: $mysqladmin"
}

& $mysqladmin -u root --protocol=tcp --host=127.0.0.1 --port=3306 shutdown
Write-Host "MySQL shutdown command issued."
