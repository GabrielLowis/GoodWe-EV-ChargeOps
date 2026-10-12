$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
Set-Location -LiteralPath $projectRoot
$pythonPath = Join-Path $projectRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) { throw 'Ambiente Python ausente; veja docs/DEVELOPMENT.md.' }
$localRoot = Join-Path $projectRoot '.local'
$existing = Join-Path $localRoot 'services.json'
if (Test-Path -LiteralPath $existing) {
    $state = Get-Content -LiteralPath $existing -Raw | ConvertFrom-Json
    $running = @($state.backend, $state.frontend) | ForEach-Object {
        Get-Process -Id $_ -ErrorAction SilentlyContinue
    }
    if ($running) {
        throw 'Há processos registrados ainda ativos. Execute scripts/stop-local.ps1 antes de iniciar novamente.'
    }
    # O desligamento encerra os processos, mas deixa este arquivo. Não apagar dados do banco.
    Remove-Item -LiteralPath $existing
}
& $pythonPath scripts/configure.py
if ($LASTEXITCODE -ne 0) { throw 'Falha ao preparar a configuração' }
& (Join-Path $PSScriptRoot 'local_postgres.ps1')
& $pythonPath scripts/create_local_databases.py
if ($LASTEXITCODE -ne 0) { throw 'Falha ao preparar os bancos' }
& $pythonPath -m backend.bootstrap
if ($LASTEXITCODE -ne 0) { throw 'Bootstrap falhou' }
$backendProc = Start-Process -FilePath $pythonPath -ArgumentList '-m','uvicorn','backend.main:app','--host','127.0.0.1','--port','8000' -WorkingDirectory $projectRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $localRoot 'backend.out.log') -RedirectStandardError (Join-Path $localRoot 'backend.err.log') -PassThru
$frontendRoot = Join-Path $projectRoot 'frontend'
$vitePath = Join-Path $frontendRoot 'node_modules/vite/bin/vite.js'
$frontendProc = Start-Process -FilePath (Get-Command node.exe).Source -ArgumentList ('"{0}"' -f $vitePath),'--host','127.0.0.1','--port','5173','--strictPort' -WorkingDirectory $frontendRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $localRoot 'frontend.out.log') -RedirectStandardError (Join-Path $localRoot 'frontend.err.log') -PassThru
@{ backend = $backendProc.Id; frontend = $frontendProc.Id } | ConvertTo-Json | Set-Content -LiteralPath $existing
function Wait-LocalHttp([string]$Address) {
    for ($attempt = 0; $attempt -lt 12; $attempt++) {
        try {
            $response = Invoke-WebRequest -Uri $Address -TimeoutSec 2
            if ($response.StatusCode -eq 200) { return }
        } catch { }
        Start-Sleep -Milliseconds 500
    }
    throw "Serviço não respondeu em $Address. Consulte os logs em .local e execute scripts/stop-local.ps1 antes de tentar novamente."
}
Wait-LocalHttp 'http://127.0.0.1:8000/api/saude'
Wait-LocalHttp 'http://127.0.0.1:5173/api/saude'
Write-Output 'Frontend: http://127.0.0.1:5173 | API: http://127.0.0.1:8000/docs'
