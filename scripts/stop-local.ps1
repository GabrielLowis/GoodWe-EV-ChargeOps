$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$statePath = Join-Path $projectRoot '.local/services.json'
if (Test-Path -LiteralPath $statePath) {
    $state = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
    foreach ($servicePid in @($state.backend, $state.frontend)) {
        $process = Get-CimInstance Win32_Process -Filter "ProcessId = $servicePid"
        if ($process -and ($process.CommandLine -match 'backend.main:app' -or $process.CommandLine.Contains((Join-Path $projectRoot 'frontend')))) {
            # O launcher de venv pode ter um filho Python. Pare somente filhos da instância identificada.
            Get-CimInstance Win32_Process -Filter "ParentProcessId = $servicePid" | ForEach-Object { Stop-Process -Id $_.ProcessId -ErrorAction SilentlyContinue }
            Stop-Process -Id $servicePid -ErrorAction SilentlyContinue
        }
    }
    Remove-Item -LiteralPath $statePath
}
& (Join-Path $PSScriptRoot 'local_postgres.ps1') -Mode Stop
