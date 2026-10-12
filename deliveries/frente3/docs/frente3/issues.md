# Frente 3 - Issues no modelo do plano (seção 14)

Cada bloco pode virar uma Issue no GitHub. Ao fazer o commit correspondente, cite a issue na mensagem
(ex.: `feat(rateio): divide sessão por faixa horária (closes #12)`) para o histórico mostrar o processo.

---

### [BANCO] Schema inicial e migration 0001

| Campo | Conteúdo |
|---|---|
| Contexto | O plano define o modelo mínimo: User, CondoUnit, Charger, Reservation, ChargingSession, Tariff, Invoice, InvoiceItem, Anomaly, AuditEvent. |
| Entrada | Modelo de dados do plano; stack da Sprint 1 (PostgreSQL 16, SQLAlchemy, Alembic). |
| Saída | `backend/migrations/versions/0001_schema_inicial.py`, `backend/db/models.py`, `backend/db/enums.py`. |
| Critérios de aceite | `alembic upgrade head` cria as 16 tabelas do zero; `downgrade base` remove tudo; ORM e migration sem divergência. |
| Dependências | Nenhuma (destrava as outras frentes). |
| Testes | `backend/tests/db/test_migrations.py` |
| Responsável | Mayara (Frente 3) |
| Labels | sprint-2, banco, P0 |

### [BANCO] Regras de integridade no PostgreSQL

| Campo | Conteúdo |
|---|---|
| Contexto | Plano, seção 5: sessão não cobrada duas vezes; reservas sem sobreposição; tarifas versionadas; fatura fechada imutável; revisão de anomalia auditada. |
| Entrada | Schema da issue anterior. |
| Saída | Restrições `EXCLUDE`, FKs compostas, `CHECK` e gatilhos na migration 0001. |
| Critérios de aceite | Cada regra recusada pelo banco mesmo com `UPDATE` direto; erro aparece como `IntegrityError`. |
| Dependências | Schema inicial. |
| Testes | `backend/tests/db/test_integrity.py` |
| Responsável | Mayara (Frente 3) |
| Labels | sprint-2, banco, P0 |

### [RATEIO] Dividir sessão que atravessa faixas tarifárias

| Campo | Conteúdo |
|---|---|
| Contexto | Plano: "não use simplesmente a tarifa do horário inicial para toda a sessão". |
| Entrada | Sessão (início, fim da energia, kWh Green/Grid, curva de potência opcional), tarifa com janelas, feriados, fuso. |
| Saída | Trechos por faixa com kWh e valor; método usado registrado na memória. |
| Critérios de aceite | 17:30-18:00 intermediário + 18:00-20:30 ponta; soma dos trechos = kWh medido; fim de semana e feriado fora de ponta. |
| Dependências | Schema de Tariff e ChargingSession. |
| Testes | `test_bands.py`, `test_allocation.py`, `test_exemplo_do_plano_calculado_por_faixa` |
| Responsável | Mayara (Frente 3) |
| Labels | sprint-2, rateio, P0 |

### [RATEIO] Calcular ociosidade após tolerância de 15 minutos

| Campo | Conteúdo |
|---|---|
| Contexto | A Sprint 1 define taxa de overstay após 15 min do fim da carga. |
| Entrada | Sessão, fim de fluxo de energia, fim de ocupação, tarifa/min. |
| Saída | `idle_minutes`, `idle_amount` e memória de cálculo. |
| Critérios de aceite | 14 min = R$ 0; 15 min = R$ 0; 16 min = 1 min cobrado; falha do sistema = R$ 0. |
| Dependências | Schema ChargingSession + Tariff; campo `energy_ended_at` no SessionDTO (Frente 1). |
| Testes | `backend/tests/rateio/test_idle.py` |
| Responsável | Mayara (Frente 3) |
| Labels | sprint-2, rateio, P0 |

### [RATEIO] Imposto e overhead parametrizáveis com vigência

| Campo | Conteúdo |
|---|---|
| Contexto | Frente 2 da Sprint 1: imposto em disputa (ICMS x ISS) e em transição (IBS/CBS); overhead pode ser 0%. |
| Entrada | Subtotal da sessão, regras de `tax_rules` vigentes, percentual de overhead da tarifa. |
| Saída | Linha por imposto (base, alíquota, valor) e overhead. |
| Critérios de aceite | Vários impostos ao mesmo tempo; exclusão opcional da energia compensada; overhead 0% aceito; alíquota faturada não muda. |
| Dependências | Schema TaxRule e Tariff. |
| Testes | `test_imposto_e_overhead_incidem_sobre_o_subtotal`, `test_varios_impostos_na_transicao_ibs_cbs`, `test_exclusao_da_energia_compensada_da_base_do_imposto` |
| Responsável | Mayara (Frente 3) |
| Labels | sprint-2, rateio, P0 |

### [RATEIO] Casos excepcionais da Sprint 1

| Campo | Conteúdo |
|---|---|
| Contexto | Sessão interrompida, morador sem uso, dois veículos da mesma unidade, no-show (Sprint 1, seção 6.4). |
| Entrada | `end_status` da sessão; faturas por morador. |
| Saída | Regras `normal`, `user_stopped_no_idle`, `system_failure_no_charge`; fatura zero. |
| Critérios de aceite | Falha = linha R$ 0 com motivo; encerrada pelo morador = só energia; sem uso = R$ 0; dois moradores = duas faturas. |
| Dependências | Motor de rateio. |
| Testes | `test_engine.py`, `test_faturamento.py` |
| Responsável | Mayara (Frente 3) |
| Labels | sprint-2, rateio, P0 |

### [FATURA] Gerar e fechar a fatura mensal com memória de cálculo

| Campo | Conteúdo |
|---|---|
| Contexto | A fatura soma as sessões aprovadas; a memória de cálculo precisa reproduzir o valor (checklist da Sprint 2). |
| Entrada | Sessões aprovadas do morador, tarifas e impostos vigentes em cada sessão. |
| Saída | `invoices` + `invoice_items` com memória em JSONB; fechamento imutável; auditoria. |
| Critérios de aceite | Recalcular fatura aberta é idempotente; sessão liberada depois entra como lançamento posterior; memória reproduz o valor. |
| Dependências | Motor de rateio; validação de anomalias (Frente 4). |
| Testes | `backend/tests/db/test_faturamento.py` |
| Responsável | Mayara (Frente 3) |
| Labels | sprint-2, fatura, P0 |

### [RELATÓRIO] Relatório de arrecadação para o síndico

| Campo | Conteúdo |
|---|---|
| Contexto | Painel do síndico: "Financeiro - arrecadação mensal e relatórios"; reembolso ao condomínio (Sprint 1, 6.3). |
| Entrada | Faturas e sessões do mês. |
| Saída | Totais por morador, reembolso de energia, imposto a recolher, balanço de energia (faturada x não faturada). |
| Critérios de aceite | Total do relatório = soma das faturas; kWh entregues = soma dos grupos do balanço. |
| Dependências | Geração de faturas. |
| Testes | `test_relatorio_de_arrecadacao_fecha_com_as_faturas_e_com_a_energia` |
| Responsável | Mayara (Frente 3) |
| Labels | sprint-2, fatura, P1 |

### [EVIDÊNCIA] Demo, notebook e testes no CI

| Campo | Conteúdo |
|---|---|
| Contexto | Rubrica: evidências de funcionamento (2,0 pontos). |
| Entrada | Seed de demonstração (setembro/2026). |
| Saída | `scripts/demo_frente3.py`, `notebooks/frente3_motor_de_rateio.ipynb`, `evidencias/frente3/`, workflow do GitHub Actions. |
| Critérios de aceite | Demo roda do zero com um comando; notebook executado com saídas; testes passam no CI. |
| Dependências | Todas as anteriores. |
| Testes | O próprio CI |
| Responsável | Mayara (Frente 3) |
| Labels | sprint-2, devops, P0 |
