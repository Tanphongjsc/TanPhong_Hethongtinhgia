param([Parameter(ValueFromRemainingArguments = $true)][string[]]$TestArguments)
$ErrorActionPreference = 'Stop'
$env:APP_ENV = 'test'
$env:DJANGO_SETTINGS_MODULE = 'config.test_settings'
$taskRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$taskCluster = [System.IO.Path]::GetFullPath((Join-Path $taskRoot '.test-postgres'))
if (-not $taskCluster.StartsWith($taskRoot + [System.IO.Path]::DirectorySeparatorChar, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw 'Test cluster must remain inside the workspace.'
}
$taskPgBin = $env:COSTING_PG_BIN
if (-not $taskPgBin) { $taskPgBin = 'C:\Program Files\PostgreSQL\17\bin' }
if (-not (Test-Path -LiteralPath (Join-Path $taskPgBin 'initdb.exe'))) { throw 'Set COSTING_PG_BIN to your local PostgreSQL bin directory.' }
$taskPort = 55432
$env:COSTING_TEST_DB_PORT = "$taskPort"
if (-not (Test-Path -LiteralPath (Join-Path $taskCluster 'PG_VERSION'))) {
    & (Join-Path $taskPgBin 'initdb.exe') -D $taskCluster -U costing_test -A trust --encoding=UTF8 --locale=C
    if ($LASTEXITCODE -ne 0) { throw 'Cannot initialize isolated test PostgreSQL.' }
}
$taskStarted = $false
try {
    & (Join-Path $taskPgBin 'pg_ctl.exe') -D $taskCluster -l (Join-Path $taskCluster 'server.log') -o "-p $taskPort -h 127.0.0.1" -w start
    if ($LASTEXITCODE -ne 0) { throw 'Cannot start isolated PostgreSQL; check port 55432.' }
    $taskStarted = $true
    Push-Location -LiteralPath $taskRoot
    try {
        & (Join-Path $taskRoot 'env\Scripts\python.exe') manage.py test --settings=config.test_settings --noinput @TestArguments
        $taskResult = $LASTEXITCODE
    } finally { Pop-Location }
} finally {
    if ($taskStarted) { & (Join-Path $taskPgBin 'pg_ctl.exe') -D $taskCluster -m fast -w stop }
}
exit $taskResult
