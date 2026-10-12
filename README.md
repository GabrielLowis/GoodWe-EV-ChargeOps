# EV ChargeOps — GoodWe × FIAP

Projeto integrado com as quatro entregas da Frente 5: backend FastAPI, PostgreSQL com migrations, rateio auditável da Frente 3, detector da Frente 4 e frontend React + TypeScript + Vite.

**Estado em 11/10/2026:** frontend das quatro entregas implementado, com reservas, recargas, faturas, recomendação, operação do síndico, financeiro e consulta de parâmetros. Acrescentados mostrar/ocultar senha e reservas futuras/sessões recentes no dashboard. Build e 26 testes aprovados, com percurso atual integrado à API e contingência PWA no navegador. Revisão de anomalia persistida aguarda uma ocorrência disponível; instalação PWA em aparelho não foi validada. O equipamento GoodWe real ainda não está conectado. As entregas originais foram preservadas em `deliveries/`.

- [Execução do frontend e URLs locais](frontend/EXECUCAO.md)
- [Roteiro da apresentação das quatro entregas](frontend/APRESENTACAO.md)
- [Resultados e pendências da entrega 4](frontend/ENTREGA4.md)
- [Validação final e evidências atuais](frontend/VALIDACAO-FINAL.md)

## Iniciar

Com Python 3.12 e Docker Compose instalados:

```powershell
python scripts/configure.py
docker compose up --build
```

O script cria `.env` apenas se estiver ausente, com segredos locais aleatórios. O Compose aguarda banco saudável, aplica migrations, recompõe o modelo e cria contas de demonstração somente quando `SEED_DEMO=true` e o banco ainda não possui usuários.

- Frontend: http://localhost:5173
- Swagger: http://localhost:8000/docs
- Saúde completa: http://localhost:8000/api/saude
- Contas de demonstração: `sindico@demo.local` e `morador@demo.local`; senha em `DEMO_PASSWORD` no `.env`.

Neste computador também foi preparado um ambiente nativo, sem instalar serviço do Windows. Iniciar: `./scripts/start-local.ps1`. Encerrar: `./scripts/stop-local.ps1`. Ambos usam apenas os processos e o banco deste projeto. Veja [desenvolvimento local](docs/DEVELOPMENT.md).

## Demonstração do fluxo integrado

```powershell
docker compose --profile demo run --rm simulator
```

No ambiente nativo:

```powershell
./.venv/Scripts/python.exe scripts/simulate.py
```

O simulador autentica as contas de demo, cria uma reserva, envia uma sessão explicitamente simulada pela API, passa pelo detector, registra eventual revisão humana demonstrativa e gera uma fatura pelo motor real. A simulação usa horários futuros para acelerar a demonstração. Não gera cobrança nem transação financeira externa.

## Documentação para o frontend

- [Plano atual: quatro entregas e limites para o prazo de 13/10/2026](docs/ENTREGAS-FRENTE5.md) — prevalece sobre o escopo amplo.
- [Relatório original de escopo amplo, preservado como referência](docs/PLANEJAMENTO-FRENTE5.md)
- [Escopo, telas, contratos e estados da Frente 5](docs/FRONTEND.md)
- [Decisões de integração e diferenças entre entregas](docs/INTEGRATION.md)
- [Comandos, testes e operação do ambiente](docs/DEVELOPMENT.md)
- [Resultados e limitações da validação](docs/VALIDATION.md)
- [Contrato OpenAPI gerado](docs/openapi.json)

## Organização

| Pasta | Uso |
|---|---|
| `backend/api` | REST, autenticação, reservas, ingestão e adaptação entre frentes |
| `backend/db`, `backend/migrations` | Schema PostgreSQL canônico, restrições e auditoria |
| `backend/rateio`, `backend/faturamento` | Cálculos, faturas e relatórios da Frente 3 |
| `condocharge_ai`, `data` | Detector e CSVs recebidos na Frente 4 |
| `frontend` | Telas dos dois perfis, cliente tipado, autenticação em memória e infraestrutura PWA |
| `scripts`, `infra` | Configuração, simulador e banco de desenvolvimento |
| `deliveries` | Referência preservada das entregas originais; não executada pelo projeto integrado |
| `docs/reference` | Documentação recebida para contexto acadêmico |

Não há pagamentos, API real SEMS, gateway Modbus ou recomendação treinada com regressão. A recomendação disponível é um baseline determinístico com premissas retornadas pela API. A PWA tem manifest, ícones e contingência de navegação testada no build local; reservas e faturas exigem a API, e instalação em aparelho não foi comprovada.
