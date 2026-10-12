# Executar o EV ChargeOps

Frontend das entregas 1–4 e resolução dos cinco achados, conferidos em 12/10/2026 para apresentação em 13/10. Resultado atual: [RESOLUCAO-OVERVIEW.md](RESOLUCAO-OVERVIEW.md); conferência histórica de 11/10: [VALIDACAO-FINAL.md](VALIDACAO-FINAL.md). Este documento preserva a operação do banco dos autores; publicação e pacote são conferidos em [VALIDACAO-ENTREGA](../docs/VALIDACAO-ENTREGA.md).

Para instalar em outro computador, comece no [README](../README.md) e no [guia de primeira execução](../docs/DEVELOPMENT.md#primeira-instalação-nativa-no-windows). Os IDs deste roteiro não são distribuídos pelo clone.

## Endereços e contas

| URL local | Uso |
|---|---|
| http://127.0.0.1:5173 | Desenvolvimento integrado à API |
| http://127.0.0.1:4173 | Preview do build com PWA |
| http://127.0.0.1:8000/docs | Swagger da API |
| http://127.0.0.1:8000/api/saude | Saúde do banco, schema e modelo |

Primeiro consulte a saúde e abra o frontend. Reutilize serviços ativos. Em 11/10 a saúde respondeu `status=ok`, `database=ok`, `schema_version=0001_schema_inicial`, `ai_model=v1.0.0`. Os serviços estavam inicialmente parados e foram iniciados individualmente com o cluster existente.

Contas consultadas na API: `morador@demo.local` (resident, A-101) e `sindico@demo.local` (manager). Use a senha local em `DEMO_PASSWORD` do `.env` da raiz; não publique seu valor. Não precisa cadastrar usuários. Token em memória: sair ou recarregar exige novo login.

## Preservar e iniciar somente o ambiente existente dos autores

Na raiz, confira se a API está ativa:

```powershell
cd "C:\Users\Gabriel Luis\Documents\ChatGPT\GoodWe"
Invoke-RestMethod http://127.0.0.1:8000/api/saude
```

Se os serviços estiverem parados, use os comandos abaixo, cada serviço em seu terminal. O cluster deve existir. Não execute `start-local.ps1` para repetir esta conferência: esse helper também chama configure, criação de bancos e bootstrap. Esses passos preparam um ambiente novo; para preservar este conjunto, reutilize somente o cluster existente.

```powershell
if (-not (Test-Path .local/pgdata/PG_VERSION)) { throw 'Cluster existente ausente; interromper sem inicializar.' }
.\scripts\local_postgres.ps1
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Em outro terminal na raiz:

```powershell
npm --prefix frontend run dev -- --host 127.0.0.1
```

Esses comandos foram utilizados nesta conferência (API e Vite lançados em segundo plano com janela oculta). O PostgreSQL portátil usa os dados existentes em `.local/pgdata`. Não apague o cluster, rode SQL, migrations, seeds, bootstrap ou simulador. Em outro computador consulte `docs/DEVELOPMENT.md`; dependências e Docker não foram montados nesta meta.

Para parar os serviços lançados manualmente, use Ctrl+C nos terminais respectivos. Nesta máquina os processos em segundo plano são registrados em `.local/services.json`; o helper `stop-local.ps1` encerra esses processos e o banco do projeto. Não pare serviços durante a apresentação.

## Testes, build e preview

Na raiz:

```powershell
npm --prefix frontend test
npm --prefix frontend run build
npm --prefix frontend run preview -- --strictPort
```

Só inicie o preview se 4173 não responder. Usa o proxy `/api` para a API 8000; API/banco permanecem ativos. O preview em segundo plano fica identificado em `.local/preview-services.json`. Encerre com Ctrl+C se iniciado no seu terminal. Para encerrar o processo registrado, confira nome e linha de comando antes:

```powershell
$previewState = Get-Content .local/preview-services.json -Raw | ConvertFrom-Json
$previewProcess = Get-CimInstance Win32_Process -Filter "ProcessId = $($previewState.preview)"
if ($previewProcess.Name -eq 'node.exe' -and $previewProcess.CommandLine -match 'vite.js.*preview.*4173') {
    Stop-Process -Id $previewState.preview
}
```

O worker registra somente em produção. Guarda a página de contingência; reservas, login e faturas dependem da API. Instalação física não comprovada. A prova histórica de contingência está em `evidence/entrega4/15-offline-producao.jpg`; a conferência atual está em VALIDACAO-FINAL.

## Repetir a apresentação

Siga [APRESENTACAO.md](APRESENTACAO.md), em 8–10 minutos. Consulte a reserva #9 de 13/10, 09h–10h, e a falta simulada #3. Sugestões são dinâmicas; abra rascunhos sem confirmar para preservar o conjunto. Outubro permanece aberto, R$ 4,04; novembro tem fatura zero fechada de teste histórico anterior à nova regra. Não recalcular/fechar faturas para repetir evidência.

Não há telemetria física ou pagamentos. A anomalia #1 permanece pendente e #2 tem rejeição persistida pela interface, ambas simuladas e sem energia. Aprovação humana e atribuição órfã persistidas não foram executadas nesta resolução.

## Credenciais em uma instalação nova

Use `morador@demo.local` e `sindico@demo.local` com `DEMO_PASSWORD` do `.env` criado pelo configurador daquela instalação. O seed só cria as contas em banco vazio e não altera senhas existentes. Arquivos privados de senhas dos autores ficam fora do Git/ZIP e não são necessários ao avaliador.

