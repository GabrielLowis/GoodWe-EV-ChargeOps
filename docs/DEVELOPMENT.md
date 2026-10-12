# Desenvolvimento e execução

Para começar a avaliação, leia o [README](../README.md) e o [percurso acadêmico](ENTREGA-ACADEMICA.md). Este documento separa uma **primeira instalação** da reutilização do banco demonstrativo dos autores. A conferência prática da cópia isolada fica em [VALIDACAO-ENTREGA](VALIDACAO-ENTREGA.md).

## Primeira instalação nativa no Windows

Requisitos: Python 3.12, Node.js 24/npm e PostgreSQL 16. Os binários PostgreSQL não estão no ZIP/repositório; use uma instalação administrada por você ou a opção portátil abaixo. A configuração padrão usa 5432 (banco), 8000 (API) e 5173 (frontend); reserve portas livres.

Na pasta extraída/clonada, que contém README e requirements.txt:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
npm.cmd --prefix frontend ci
.\.venv\Scripts\python.exe scripts/configure.py
```

O configurador cria `.env` e `frontend/.env.local` apenas se ausentes. Banco/JWT recebem segredos locais aleatórios. Consulte `DEMO_PASSWORD` no `.env` criado; o valor demonstrativo do template é público e serve apenas para testes. `SEED_DEMO=true` cria os dois perfis e parâmetros quando a tabela de usuários está vazia. Bootstrap posterior preserva senhas/registros existentes.

### Opção A — PostgreSQL portátil

Baixe os [binários indicados pelo PostgreSQL para Windows](https://www.postgresql.org/download/windows/), versão 16, e extraia a árvore `pgsql` para `.local`. Deve existir `.local/pgsql/bin/pg_ctl.exe`, junto com `pgsql/lib` e `pgsql/share`. Não é necessário instalar um serviço Windows.

Na raiz:

```powershell
.\scripts\start-local.ps1
```

O script existente inicializa seu cluster local se ausente, cria `evchargeops` e `evchargeops_test`, aplica migrations da Frente 3, recompõe o modelo ativo se ausente e inicia API/Vite. Logs e PIDs ficam em `.local`. Em caso de erro, confira os logs; não apague o cluster para tentar novamente. Para encerrar os processos iniciados por esse helper:

```powershell
.\scripts\stop-local.ps1
```

Se a porta 5432 já tem outro PostgreSQL, use a opção B. O helper portátil foi escrito para a porta padrão; não o utilize para administrar um cluster preexistente externo.

### Opção B — PostgreSQL já administrado

Crie um usuário com permissão para seus dois bancos e configure `DATABASE_URL` e `TEST_DATABASE_URL` no `.env`. O banco de teste precisa ser **distinto e terminar em `_test`**. A suíte pode remover e recriar suas tabelas.

Exemplo, executado no `psql` por um administrador PostgreSQL: substitua a senha abaixo pelo `POSTGRES_PASSWORD` do seu `.env` antes de executar. Se usuário/bancos já existem, apenas confira o proprietário e as URLs; não recrie nem apague dados.

```sql
CREATE ROLE evcharge LOGIN PASSWORD 'SENHA_DO_POSTGRES_PASSWORD_NO_ENV';
CREATE DATABASE evchargeops OWNER evcharge;
CREATE DATABASE evchargeops_test OWNER evcharge;
```

URLs padrão do `.env`, com a senha real local, apontam para `127.0.0.1:5432`. Se seu servidor usa outra porta, ajuste ambas as URLs. Com banco e dependências presentes, execute na raiz:

```powershell
.\.venv\Scripts\python.exe -m backend.bootstrap
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Em outro terminal:

```powershell
npm.cmd --prefix frontend run dev
```

Bootstrap usa migrations, nunca `create_all`; reconstrói o artefato ativo dos CSVs e cria demo somente se autorizado por `SEED_DEMO`. Se trocar a porta da API, ajuste `API_PROXY_TARGET` em `frontend/.env.local` e `API_URL` usado pelo simulador. Se trocar a porta do frontend, inclua sua origem em `CORS_ORIGINS` no `.env` do backend.

### Saúde, acesso e dados demonstrativos

- Aplicativo: http://127.0.0.1:5173
- Swagger: http://127.0.0.1:8000/docs
- Saúde: http://127.0.0.1:8000/api/saude
- Contas: `morador@demo.local` e `sindico@demo.local`, ambas com `DEMO_PASSWORD` da sua configuração. Recarregar exige login novamente.

Confirme saúde e prepare **uma vez** os dados em banco novo de demonstração:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/saude
.\.venv\Scripts\python.exe scripts/simulate.py
```

O script realiza HTTP real contra a API local, mas envia sessão **simulada** com horários futuros, sem integração física. Imprime IDs para o percurso. Use mês/ano do início da sessão em São Paulo para localizar a fatura/relatório; não presuma período ou IDs das capturas. Reexecutar cria novos registros e pode recalcular fatura aberta. Uma fatura fechada não é reaberta; o script não substitui cadastros. Fila de anomalias pode ficar vazia.

## Preservar o ambiente existente dos autores

O computador dos autores já possui `.venv`, dependências, PostgreSQL portátil e banco demonstrativo. Esses itens não acompanham o pacote. Para apresentar esse conjunto, use [EXECUCAO](../frontend/EXECUCAO.md) e [APRESENTACAO](../frontend/APRESENTACAO.md); não repita bootstrap/seed/simulador para reproduzir capturas históricas.

IDs/datas desse roteiro descrevem o estado de 12/10. Não se aplicam automaticamente a um clone. A validação de primeira instalação usa cópia, configuração, cluster e portas separados, preservando os serviços/dados originais.

## Alternativa Docker Compose

Pré-requisitos: Python 3.12 para o configurador e Docker Compose. Containers estão preparados, mas **não foram executados neste computador**, que não possui Docker. Não tratar essa alternativa como validação prática realizada.

```powershell
python scripts/configure.py
docker compose up --build
# Em outro terminal:
docker compose --profile demo run --rm simulator
```

Compose usa volume `postgres_data`. `docker compose stop` encerra sem apagar os dados. Inicializa o modelo e as migrations pelo bootstrap. O proxy do frontend aponta para `http://backend:8000`; no Vite nativo aponta para `http://127.0.0.1:8000`.

Para desenvolver somente o frontend com backend/banco em containers:

```powershell
docker compose up --build db backend
npm.cmd --prefix frontend ci
npm.cmd --prefix frontend run dev
```

`VITE_API_BASE_URL` contém apenas a origem da API, sem `/api`; vazio usa proxy. Variáveis VITE são públicas: não inserir senhas/JWT nelas.

## Configuração

| Variável | Uso |
|---|---|
| DATABASE_URL | PostgreSQL principal; nunca enviado ao navegador |
| TEST_DATABASE_URL | Banco descartável distinto, terminado em `_test` |
| JWT_SECRET | Pelo menos 32 caracteres; gerado pelo configurador |
| CORS_ORIGINS | Origens permitidas separadas por vírgula |
| CONDO_TIMEZONE | America/Sao_Paulo por padrão |
| TAX_JURISDICTION | Seleção das regras tributárias cadastradas |
| SEED_DEMO / DEMO_PASSWORD | Contas/parâmetros fictícios de demonstração |
| VITE_API_BASE_URL | Origem pública da API; vazio usa proxy |
| API_PROXY_TARGET | Destino do proxy Vite, somente no servidor local |
| API_URL | URL completa para o simulador, incluindo `/api` |

## Testes e build

Na raiz, com banco exclusivo de teste acessível:

```powershell
.\.venv\Scripts\python.exe -m condocharge_ai.training.train
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
.\.venv\Scripts\python.exe -m ruff check backend condocharge_ai scripts tests
npm.cmd --prefix frontend test
npm.cmd --prefix frontend run build
```

Os testes de banco fazem downgrade/upgrade **somente em TEST_DATABASE_URL terminado em `_test`**. Banco indisponível é falha, não prova de integração. Jamais aponte a suíte ao banco principal.

Com Compose ativo:

```powershell
docker compose exec backend python -m pytest -q -p no:cacheprovider
docker compose exec frontend npm test
docker compose exec frontend npm run build
```

O workflow existente verifica banco, treino, testes, lint, build e contratos. Resultado remoto será registrado após a publicação, sem presumir aprovação.

## Atualizar o contrato durante desenvolvimento

Somente após alterar schemas/rotas:

```powershell
.\.venv\Scripts\python.exe -m scripts.export_openapi
npm.cmd --prefix frontend run api:generate
```

O cliente é gerado do OpenAPI; não editar manualmente uma segunda definição dos schemas. Esta preparação acadêmica não altera APIs nem tipos.

## Diagnóstico

- API não responde: confira porta e logs do uvicorn.
- Saúde falha: confira DATABASE_URL, migrations e bootstrap/modelo na instalação nova.
- Login demo falha: confira a senha da configuração usada no primeiro seed; seed posterior não a substitui.
- Dados vazios: normal antes do simulador; não inserir medições para fingir telemetria real.
- Reserva em conflito: escolha outra janela futura livre; disponibilidade continua sujeita à validação do POST.
- Fechamento recusado: aguarde o término do período; fechado não comprova pagamento.

O healthcheck não valida comunicação SEMS/Modbus. Para limites e decisões, consulte [INTEGRATION](INTEGRATION.md).
