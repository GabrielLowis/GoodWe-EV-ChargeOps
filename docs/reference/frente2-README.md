# EV ChargeOps - Back-end (Sprint 2)

Back-end do EV ChargeOps: recebe sessoes de recarga de veiculos eletricos, descobre de qual morador e cada
sessao, valida se ela faz sentido, calcula o rateio e gera a fatura mensal com memoria de calculo auditavel.

## Fluxo implementado

```
Sessao (SessionDTO) -> Atribuicao a reserva -> Validacao (camadas 1, 2 e 3) -> Rateio -> Fatura -> API
                                                   |
                                         suspeita ou orfa -> fila do sindico -> aprovar / rejeitar
```

1. `POST /sessoes` recebe a sessao no formato do contrato (`SessionDTO`).
2. A sessao e atribuida a reserva ativa do carregador cuja janela contem o horario de inicio.
   Sem reserva correspondente, a sessao e marcada como orfa e vai para a fila do sindico.
3. O modulo de anomalias roda em camadas e para na primeira que falhar: (1) estrutural, (2) fisica,
   (3) modelo de ML. Sessao suspeita ou orfa nao entra na fatura ate o sindico revisar.
4. Sessoes aprovadas entram no motor de rateio quando a fatura do mes e gerada.

## Como executar

Requisitos: Python 3.10 ou superior e Docker.

```
docker start chargeops-db            # PostgreSQL (primeira vez: ver docker run abaixo)
python -m venv .venv
.venv\Scripts\Activate.ps1           # Windows PowerShell
pip install -r requirements.txt
copy .env.example .env               # e ajuste DB_PASSWORD
python models.py                     # cria as tabelas
python seed.py                       # dados de demonstracao
uvicorn main:app --reload
```

Primeira vez, para criar o banco:

```
docker run --name chargeops-db -e POSTGRES_USER=chargeops -e POSTGRES_PASSWORD=<sua senha> -e POSTGRES_DB=chargeops -p 5432:5432 -d postgres:16
```

Documentacao interativa: http://localhost:8000/docs (use o botao Authorize com o token do `POST /login`).

Usuarios do seed: `sindico@demo.com` (Gestor) e `morador@demo.com` (Morador); senhas em `.env.example`.
Os valores de tarifa do seed sao ficticios, so para demonstrar o calculo.

Como o projeto ainda nao usa migrations, mudancas de estrutura exigem recriar as tabelas:

```
docker exec -it chargeops-db psql -U chargeops -d chargeops -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
python models.py
python seed.py
```

## Testes

```
python -m pytest
```

Os testes usam SQLite em memoria (nao precisam do PostgreSQL). Resultado da ultima execucao em
`docs/evidencia-testes.txt`. Exemplo de sessao ingerida e fatura gerada, com memoria de calculo, em
`docs/exemplo-fatura.json`.

Casos cobertos: conflito de reservas no mesmo carregador, capacidade simultanea, atribuicao da sessao ao
morador correto, cancelamento e no-show apos 20 minutos com reincidencia, tolerancia de 15 minutos de
ociosidade (14, 15 e 16 minutos e falha do sistema), sessao que atravessa faixas tarifarias, formula do rateio
(Green, Grid, ociosidade, imposto e overhead), bloqueio de sessao fisicamente impossivel, fila e revisao do
sindico com auditoria, fatura sem cobranca duplicada, fatura fechada imutavel, versionamento de tarifas e
permissoes por perfil.

## Estrutura

```
main.py            aplicacao FastAPI e registro das rotas
database.py        engine e sessao do SQLAlchemy
models.py          tabelas (SQLAlchemy)
schemas.py         contratos da API (Pydantic), incluindo o SessionDTO
security.py        hash de senha, JWT e controle de acesso por perfil
seed.py            dados de demonstracao
routers/           endpoints por assunto
services/          regras de negocio (rateio, pipeline, faturamento, reservas)
ai/                modulo de anomalias e recomendacao de janela
tests/             testes automatizados (pytest)
docs/              evidencias e guia do codigo
```

## Endpoints principais

| Metodo e rota | Perfil | Funcao |
|---|---|---|
| POST /usuarios, POST /login, GET /usuarios/eu | publico / logado | cadastro de morador, login, perfil |
| POST /reservas, GET /reservas, POST /reservas/{id}/cancelar | logado | reservas |
| POST /reservas/no-show/processar | gestor | cancela no-show e registra reincidencia |
| POST /sessoes, GET /sessoes | ingestao aberta / logado | sessoes de recarga |
| GET /anomalias, POST /anomalias/{id}/revisao | gestor | fila do sindico |
| POST /tarifas, POST /configuracao-cobranca | gestor | faixas, ociosidade, imposto, overhead |
| POST /faturas/gerar, GET /faturas, POST /faturas/{id}/fechar | gestor / logado | faturas |
| GET /relatorios/arrecadacao | gestor | fechamento mensal |
| GET /recomendacao-janela | logado | melhor horario e custo previsto |

## Decisoes tecnicas

- **Rateio por funcoes puras.** O calculo (`services/rateio.py`) nao acessa o banco, o que permite testa-lo isolado.
  Cada parcela e arredondada para centavos antes da soma, para que a fatura possa ser conferida a mao.
- **Dinheiro em `Decimal` / `Numeric`.** Valores monetarios e tarifas nunca usam `float`.
- **Memoria de calculo em JSONB.** Cada item da fatura guarda tarifas, parametros e trechos usados. Alterar a tarifa
  atual nao muda faturas antigas, e fatura fechada recusa novas sessoes.
- **Tarifas versionadas por validade.** A mesma faixa pode ter varias versoes; vale a mais recente na data da sessao.
- **Atribuicao por intervalo de tempo.** A sessao vai para a reserva ativa do carregador cuja janela contem o inicio.
- **Auditoria.** Reservas, ingestao, revisoes de anomalia, tarifas e faturas geram registros em `audit_events`.
- **Senhas.** Armazenadas como hash PBKDF2 com salt; autenticacao por JWT.

## Desvios em relacao a Sprint 1 e premissas a validar

- **Sessao sem reserva.** A Sprint 1 previa atribuir ao dono cadastrado do cartao RFID. Como o cartao e compartilhado,
  seguimos o plano da Sprint 2: a sessao fica orfa e o sindico indica o morador.
- **Status da sessao.** O contrato so previa `completed`. Adicionamos `failed` para a regra de que falha do sistema
  nao gera cobranca. A confirmar com as demais frentes.
- **Ociosidade estimada.** A SEMS nao informa o fim do fluxo de energia. Estimamos o tempo de carga como
  `total_kwh / max_power_kw` e tratamos o restante da sessao como ociosidade, sujeita a tolerancia de 15 minutos.
- **Sessao entre faixas.** Sem curva de potencia minuto a minuto, a energia e distribuida entre as faixas
  proporcionalmente ao tempo (potencia constante).
- **Recomendacao de janela.** Implementada como baseline deterministico (curva solar simplificada e tarifas vigentes).
  O modelo de regressao previsto na Sprint 1 ainda nao esta integrado.
- **Camada 3 da deteccao de anomalias.** A fachada ja chama `ai/ml_model.py` quando o arquivo existe
  (`score_session(sessao) -> (score, suspeita, motivos)`). Ate la, apenas as camadas 1 e 2 estao ativas.
- **Fuso horario.** Horarios sao guardados sem fuso. Definir um fuso unico entre SEMS, gateway e back-end.

## Limitacoes conhecidas

- A ingestao (`POST /sessoes`) nao exige autenticacao nesta versao; em producao deve usar chave de API.
- Integracao real com a SEMS+, gateway Modbus e reconciliacao entre as duas fontes estao fora deste modulo.
- Sem migrations (Alembic) e sem Docker Compose para o back-end.
- Sem multi-condominio, pagamentos e relatorios alem do fechamento mensal.
