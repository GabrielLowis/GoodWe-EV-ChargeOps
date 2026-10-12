# Desenvolvimento e execução

## Ambiente recomendado com Docker

Pré-requisitos: Python 3.12 para gerar a configuração e Docker Compose.

```powershell
python scripts/configure.py
docker compose up --build
```

O banco fica persistido no volume `postgres_data`. `docker compose stop` para os serviços sem apagar dados. Para executar apenas backend/banco e desenvolver o frontend no terminal:

```powershell
docker compose up --build db backend
cd frontend
npm ci
npm run dev
```

O frontend conecta ao proxy `/api`, que aponta para o backend. No container o destino é `http://backend:8000`; no Vite nativo é `http://127.0.0.1:8000`. `VITE_API_BASE_URL` pode apontar diretamente para outra origem autorizada no CORS, sem `/api` ao final.

A configuração do Compose espera os healthchecks conforme a [documentação oficial do Docker](https://docs.docker.com/compose/how-tos/startup-order/). Os Dockerfiles e Compose foram preparados; este computador não possui Docker, portanto a execução dos containers não foi testada aqui.

## Ambiente nativo preparado neste computador

O ambiente atual inclui `.venv`, dependências do frontend e PostgreSQL 16.15 portátil em `.local/pgsql`. Binários, dados do banco, segredos e arquivos gerados do modelo são ignorados no Git. Nenhum serviço do Windows foi instalado.

```powershell
./scripts/start-local.ps1
# Encerrar os processos e banco iniciados por estes scripts:
./scripts/stop-local.ps1
```

Os serviços são iniciados em segundo plano, com logs em `.local/*.log`, escutando somente em loopback. Os scripts preservam dados; não apagam o cluster.

Em outro Windows sem Docker, instalar Python 3.12 e Node 24 e preparar dependências:

```powershell
python -m venv .venv
./.venv/Scripts/python.exe -m pip install -r requirements.txt
npm --prefix frontend ci
./.venv/Scripts/python.exe scripts/configure.py
```

Para usar o helper de PostgreSQL portátil, baixar os [binários oficiais indicados pelo PostgreSQL](https://www.postgresql.org/download/windows/) e extrair `pgsql/bin`, `pgsql/lib` e `pgsql/share` dentro de `.local`. Em seguida rodar `start-local.ps1`. Se usar um PostgreSQL já administrado por você, configure DATABASE_URL e TEST_DATABASE_URL, crie os dois bancos e rode os comandos manuais abaixo; não use o helper portátil nesse caso.

Com banco configurado e dependências presentes:

```powershell
./.venv/Scripts/python.exe -m backend.bootstrap
./.venv/Scripts/python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
# Em outro terminal:
npm --prefix frontend run dev
```

`backend.bootstrap` aplica migrations e cria o modelo ativo se ausente. Só cria usuários fictícios quando SEED_DEMO=true e a tabela de usuários está vazia. Senhas não são sobrescritas em uma segunda execução.

## Configuração

| Variável | Uso |
|---|---|
| DATABASE_URL | PostgreSQL principal; nunca enviado ao frontend |
| TEST_DATABASE_URL | Banco descartável, com nome terminado em `_test` |
| JWT_SECRET | Pelo menos 32 caracteres; gerado por configure.py |
| CORS_ORIGINS | Origens autorizadas, separadas por vírgula |
| CONDO_TIMEZONE | Fuso do condomínio; padrão America/Sao_Paulo |
| TAX_JURISDICTION | Seleção das regras tributárias cadastradas |
| SEED_DEMO / DEMO_PASSWORD | Contas e dados fictícios de desenvolvimento |
| VITE_API_BASE_URL | Origem pública da API; vazio usa proxy |
| API_PROXY_TARGET | Destino do proxy Vite; configuração do servidor local |

Variáveis VITE são públicas no build; [o Vite documenta essa exposição](https://vite.dev/guide/env-and-mode.html). Não inserir segredos nelas. .env local e logs não devem ser publicados.

## Testes

Somente com um PostgreSQL exclusivo de testes disponível:

```powershell
./.venv/Scripts/python.exe -m condocharge_ai.training.train
./.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider
./.venv/Scripts/python.exe -m ruff check backend condocharge_ai scripts tests
npm --prefix frontend test
npm --prefix frontend run build
```

Os testes de banco aplicam downgrade/upgrade no banco terminado em `_test` para verificar migrations. Isso remove os dados apenas desse banco descartável. A suíte falha se o banco não estiver acessível; não apresenta testes pulados como integração concluída.

No Compose:

```powershell
docker compose exec backend python -m pytest -q -p no:cacheprovider
docker compose exec frontend npm test
docker compose exec frontend npm run build
```

A CI preparada executa o banco real, treino determinístico, testes, lint, build e sincronização de contratos. O workflow só terá evidência remota após rodar no GitHub.

## Atualizar o contrato

```powershell
./.venv/Scripts/python.exe -m scripts.export_openapi
npm --prefix frontend run api:generate
```

OpenAPI é exportado de FastAPI sem precisar do servidor em execução, conforme o mecanismo descrito na [documentação do FastAPI](https://fastapi.tiangolo.com/advanced/generate-clients/). O cliente usa paths/components gerados e openapi-fetch; não escrever manualmente uma segunda versão dos schemas.

## Demo e diagnóstico

`scripts/simulate.py` realiza chamadas HTTP reais com credenciais de demo. As contas precisam existir e SEED_DEMO precisa ter sido habilitado no bootstrap de um banco vazio. Se o código do carregador HCA01 foi removido ou a fatura do período foi fechada, use outro período/ambiente de demo; o script não reabre faturas nem substitui cadastros.

Erros de integração aparecem no Swagger e nos logs. `/api/saude` verifica banco, versão de migration e carregamento do modelo. Telemetria contínua/SEMS não é parte desse healthcheck.
