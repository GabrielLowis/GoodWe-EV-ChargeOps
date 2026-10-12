param([ValidateSet('Start','Stop')][string]$Mode = 'Start')
$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$localRoot = [IO.Path]::GetFullPath((Join-Path $projectRoot '.local'))
$pgData = [IO.Path]::GetFullPath((Join-Path $localRoot 'pgdata'))
if (-not $pgData.StartsWith($projectRoot + [IO.Path]::DirectorySeparatorChar)) { throw 'Diretório inválido' }
$pgBin = Join-Path $localRoot 'pgsql/bin'
if (-not (Test-Path -LiteralPath (Join-Path $pgBin 'pg_ctl.exe'))) { throw 'PostgreSQL portátil ausente; use Docker ou consulte docs/DEVELOPMENT.md.' }
if ($Mode -eq 'Stop') {
    & (Join-Path $pgBin 'pg_ctl.exe') -D $pgData -m fast -w stop
    if ($LASTEXITCODE -ne 0) { throw 'Não foi possível parar o banco deste projeto' }
    exit
}
$values = @{}
Get-Content -LiteralPath (Join-Path $projectRoot '.env') | ForEach-Object {
    if ($_ -match '^([A-Z_]+)=(.*)$') { $values[$matches[1]] = $matches[2] }
}
if (-not (Test-Path -LiteralPath (Join-Path $pgData 'PG_VERSION'))) {
    $passwordFile = Join-Path $localRoot 'pg-init-password.txt'
    [IO.File]::WriteAllText($passwordFile, $values.POSTGRES_PASSWORD)
    try {
        & (Join-Path $pgBin 'initdb.exe') -D $pgData -U $values.POSTGRES_USER --auth=scram-sha-256 --encoding=UTF8 --locale=C --pwfile=$passwordFile
        if ($LASTEXITCODE -ne 0) { throw 'Falha ao inicializar o banco exclusivo' }
    } finally { Remove-Item -LiteralPath $passwordFile -ErrorAction SilentlyContinue }
}
& (Join-Path $pgBin 'pg_ctl.exe') -D $pgData status *> $null
if ($LASTEXITCODE -ne 0) {
    & (Join-Path $pgBin 'pg_ctl.exe') -D $pgData -l (Join-Path $localRoot 'postgres.log') -o '-p 5432 -h 127.0.0.1' -w start
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao iniciar Postgres; veja .local/postgres.log' }
}
