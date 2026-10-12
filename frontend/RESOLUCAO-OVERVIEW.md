# Resolução dos achados D01–D05

**Concluída em 12/10/2026, São Paulo. Os cinco itens foram aprovados.** Coleta inicial às 13h20; revisões e preparação às 13h32–13h42; testes finais às 13h44; percurso final e comparação somente leitura concluídos às 16h03. A anomalia #1 permanece pendente por desenho do cenário, não por falta de trabalho nesta Meta.

Escopo: objetivo anexado `goal-objective.md`, com exceções específicas para duas regras no backend, testes e cadastro local do feriado. O diagnóstico original [OVERVIEW-DIAGNOSTICO.md](OVERVIEW-DIAGNOSTICO.md) e suas evidências foram mantidos como histórico. Evidências desta execução: [evidence/resolucao-overview/](evidence/resolucao-overview/).

## Critérios e evidências

| Item | Status | Resultado e comprovação |
|---|---|---|
| D01 — Reservas vencidas e cancelamento | **Aprovado** | API permite cancelamento somente antes do início; no início/depois retorna 409 sem alteração/auditoria. Interface dos dois perfis segue a regra, revalida no envio e atualiza no limite temporal sem recarregar. Reserva #3 reconciliada uma vez como falta simulada; #9 aparece antes do histórico. |
| D02 — Fatura atual e fechamento | **Aprovado** | Início do morador destaca outubro/#1, R$ 4,04. Futuras continuam acessíveis e identificadas. Novo fechamento de outubro só a partir de 01/11/2026 00h de São Paulo; API/UI bloqueiam antes disso. Testes no banco exclusivo comprovam instante exato e idempotência. #2 fechada permaneceu idêntica. |
| D03 — Reserva → recarga → fatura | **Aprovado** | Detalhe #1 aponta para reserva #1 e fatura #1/outubro em ambos os perfis; links de ida/volta verificados. Associação pelo id interno e item da API. Erro financeiro tem repetição, sem falso “não faturado”; períodos posteriores e estados sem item cobertos pelos testes. |
| D04 — Cenários mínimos | **Aprovado** | Uma reserva nova #9; sessões #2/#3 zero, passadas, órfãs, sem sobreposição. Anomalia #1 pendente; #2 rejeitada pela interface como síndico, com observação persistida. Reexecução da preparação reutilizou IDs, sem novos POSTs. Não houve cobrança nova. |
| D05 — Calendário demonstrativo | **Aprovado** | Um feriado de 12/10/2026 e um evento de inclusão. Segunda execução não modifica cadastro/auditoria. Teste do motor confirma fora de ponta; parâmetros explicam dependência do calendário. Fatura/snapshots anteriores preservados. |

D01: [testes de interface/relógio](evidence/resolucao-overview/d01-frontend-tests.txt), [8 casos API](evidence/resolucao-overview/d01-api-tests.txt), [reconciliação #3](evidence/resolucao-overview/d01-no-show.json), capturas [agenda](evidence/resolucao-overview/05-sindico-agenda-final.jpg), [morador](evidence/resolucao-overview/26-morador-reservas-final.jpg) e [390 px](evidence/resolucao-overview/18-mobile-sindico-agenda.jpg). Os instantes antes/no início/depois e a página mantida aberta foram comprovados com relógios controlados nos testes; não se esperou o horário futuro real para reproduzi-los no banco demonstrativo.

D02: [testes frontend](evidence/resolucao-overview/d02-frontend-tests.txt), [API/integração](evidence/resolucao-overview/d02-api-tests.txt), [início](evidence/resolucao-overview/25-morador-inicio-final.jpg), [fechamento bloqueado](evidence/resolucao-overview/09-sindico-fatura-atual.jpg), [novembro preservado](evidence/resolucao-overview/31-morador-fatura-futura-preservada.jpg). Seleção de fatura atual zero, ausência de atual, somente futuras e mudança de mês cobertas na suíte; o banco demonstrativo mantém os valores anteriores.

D03: [testes de vínculo/erro/estados](evidence/resolucao-overview/d03-frontend-tests.txt), [síndico](evidence/resolucao-overview/08-sindico-vinculo-recarga.jpg), [morador](evidence/resolucao-overview/28-morador-vinculo-recarga.jpg), [memória e vínculo inverso](evidence/resolucao-overview/29-morador-fatura-atual.jpg). Não foram criados endpoint novo, lançamento posterior ou sessão financeira adicional para reproduzir esses estados.

D04: [manifesto e IDs](evidence/resolucao-overview/scenario-manifest.json), [revisão preenchida](evidence/resolucao-overview/03-rejeicao-preenchida.jpg), [rejeição persistida](evidence/resolucao-overview/04-rejeicao-persistida.jpg), [pendente preservada](evidence/resolucao-overview/15-ocorrencia-pendente-final.jpg), [snapshot final](evidence/resolucao-overview/db-after.json). A fila pendente continua disponível para consulta; não aprovar/atribuir para fabricar consumo.

D05: [duas execuções](evidence/resolucao-overview/d05-executions.json), [6 testes](evidence/resolucao-overview/d05-tests.txt), [explicação de parâmetros](evidence/resolucao-overview/23-mobile-calendario.jpg). O feriado efetivo e sua descrição UTF-8 estão comprovados no snapshot final. Algumas strings capturadas pelo terminal no manifesto/log da inclusão sofreram perda de acentuação; os artefatos brutos foram mantidos, e não são usados como prova da grafia no banco.

## Alterações de código

| Camada | Arquivos | Comportamento |
|---|---|---|
| API | `backend/api/routes.py` | Cancelamento rejeitado com 409 se a reserva começou; preserva verificação de estado/permissão existente. |
| Faturamento | `backend/faturamento/service.py` | Compara relógio com término do mês no fuso do condomínio; mantém retorno das já fechadas. Motor, parcelas e snapshots não foram modificados. |
| Frontend | `ReservationsPage.tsx`, `utils/reservations.ts`, `hooks/useTimeBoundaries.ts` | Elegibilidade, ordem, explicação temporal e atualização por limite/foco/visibilidade; revalidação antes de confirmar. |
| Frontend | `HomePage.tsx`, `InvoicesPage.tsx`, `FinancePage.tsx`, `utils/finance.ts` | Seleção da fatura atual/anterior, períodos futuros e disponibilidade de fechamento com relógio/revalidação. |
| Frontend | `SessionsPage.tsx` | Consulta das faturas existentes, vínculo pelo id interno, mensagens comprovadas e erro/repetição. |
| Frontend | `ParametersPage.tsx` | Texto sobre feriados cadastrados e caráter demonstrativo. |
| Operação local | `scripts/register_demo_holiday.py` | Transação idempotente, restrita ao PostgreSQL loopback de desenvolvimento `evchargeops`, inclusão única e auditoria. Data existente é preservada. |
| Testes | `tests/test_overview_rules.py`, `tests/test_demo_holiday.py`, `tests/test_integration.py`; testes das páginas/hook | Limites de tempo/API sem escrita quando recusada, idempotência, estados da interface, vínculos e calendário. |

Nenhuma mudança em modelos, migrations, fórmulas financeiras, IA, autenticação, infraestrutura, dependências ou `deliveries/`. Geração OpenAPI/cliente executada; conteúdo dos dois contratos continuou idêntico. Comparação de hashes dos arquivos anteriores em [verification.json](evidence/resolucao-overview/verification.json). A comparação de arquivos abrange os módulos listados na coleta; os novos testes de raiz e documentos são registrados explicitamente acima.

## Dados locais alterados

| Registro | Alteração e efeito |
|---|---|
| Reserva #3 | `active → no_show`, única candidata ao endpoint existente, sem sessão. Falta simulada; usuário #2 continua sem bloqueio. Todos os demais campos preservados. |
| Reserva #9 | 13/10/2026 09h–10h, residente #2, HCA01/conector 1; primeira janela livre de uma hora entre 09h e 18h do dia seguinte à preparação. |
| Sessão #2 / anomalia #1 | `goal-overview-pendente-v1`, 12/10 13h26min38s–13h27min38s; zero energia/potências; `user_stopped`, `simulator`, sem reserva/morador; validação suspensa, ocorrência pendente. |
| Sessão #3 / anomalia #2 | `goal-overview-rejeitada-v1`, 12/10 13h23min38s–13h24min38s; mesmos limites de consumo/atribuição. Rejeitada pela interface às 13h38min55s, por usuário #1. |
| Feriado | 12/10/2026, “Feriado de demonstração acadêmica”, único; evento de inclusão único. |
| Auditoria | Oito eventos novos #51–#58: uma falta, uma reserva, duas detecções, duas ingestões, uma revisão e um feriado. Vinte eventos anteriores preservados; nenhum de geração/fechamento. |

Observação da rejeição: “Demonstração acadêmica: sessão simulada sem energia e sem reserva; rejeitada para cobrança. Não representa telemetria física ou pagamento.”

A revisão automática recusou duas tentativas de reconciliar #3 por considerar vigente o limite anterior de diagnóstico. Elas não foram executadas. O usuário confirmou diretamente **“Autorizo essas alterações locais”** para o conjunto específico; as ações foram realizadas sob essa autorização, sem ampliar o escopo.

### Preservação e mapa final

`Morador #2 / A-101 → reserva #1 → sessão #1 → validação approved → item #35 → fatura #1 / 2026-10 → relatório de outubro`.

[Coleta anterior](evidence/resolucao-overview/db-before.json) e [posterior](evidence/resolucao-overview/db-after.json), ambas transações explicitamente somente leitura, comprovam:

- Nenhum registro anterior excluído; única atualização anterior foi o status de #3.
- Reserva #1, sessão #1, todas as faturas, itens, memórias e snapshots integralmente iguais.
- Fatura #1 aberta, total R$ 4,04: Green R$ 0,30 + Grid R$ 3,38 + ociosidade R$ 0,00 + imposto R$ 0,18 + custo operacional R$ 0,18.
- Fatura #2 de novembro fechada/zero idêntica, inclusive fechamento antecipado histórico.
- Usuários, bloqueios, tarifas, impostos, equipamentos e unidades preservados.
- Nenhum item para sessões #2/#3; energia entregue/faturada continua 6,2 kWh.
- Relatório de outubro agora considera três sessões, duas sem morador com zero energia. O agrupamento existente prioriza falta de atribuição; por isso #3 não ocupa também o grupo financeiro “rejeitadas”. A anomalia #2 registra a rejeição corretamente. Essa diferença de agrupamento foi explicada no roteiro, sem alterar o relatório.

Coleta HTTP final: 41 consultas/logins, todas 200, somente GET e autenticação; detalhes da recarga #1 e faturas #1/#2 iguais para os dois perfis. Não se testou fechamento novo nem recalculo no banco demonstrativo. [31 verificações finais aprovadas](evidence/resolucao-overview/verification.json) e [verificador offline reproduzível](evidence/resolucao-overview/verify_final.py).

## Validação executada

| Comando/superfície | Resultado | Evidência |
|---|---|---|
| `npm --prefix frontend test` | 50 testes em 12 arquivos aprovados | [log](evidence/resolucao-overview/frontend-final-tests.txt) |
| `npm --prefix frontend run build` | TypeScript e Vite aprovados | [log](evidence/resolucao-overview/frontend-final-build.txt) |
| `.venv/Scripts/python.exe -m pytest tests/test_overview_rules.py tests/test_demo_holiday.py tests/test_integration.py backend/tests -q -p no:cacheprovider` | 150 aprovados; nenhum pulado; um aviso existente de depreciação Starlette/httpx | [log](evidence/resolucao-overview/backend-final-tests.txt) |
| `.venv/Scripts/python.exe -m scripts.export_openapi` | Concluído; contrato preservado | [log](evidence/resolucao-overview/openapi-export.txt) |
| `npm --prefix frontend run api:generate` | Concluído; tipos preservados | [log](evidence/resolucao-overview/api-generate.txt) |
| PostgreSQL de testes | URL distinta, loopback, nome `evchargeops_test`; nunca suíte no demonstrativo | Fixtures existentes e testes pontuais |
| Navegador integrado | Ambos os perfis, desktop 1280 px e celular 390 px; navegação, teclado, mensagens, detalhes e links | [índice de 44 capturas com horários/DOM](evidence/resolucao-overview/browser-checks.json) e TXT/JPG correspondentes |
| Inspeção visual | Início desktop/mobile, agenda, fechamento/memória e parâmetros; sem transbordamento horizontal nas capturas | Capturas 18, 21, 23, 25, 35 e 39 |
| Console da conferência retomada | Nenhum erro/aviso capturado | [log](evidence/resolucao-overview/browser-console.json) |
| Conferência offline de preservação | 31 critérios aprovados | [verification.json](evidence/resolucao-overview/verification.json) |

No percurso do morador: início, reservas, nova reserva/rascunho sem envio, recomendação, recargas/detalhe, faturas/lista/detalhes e memória. No síndico: início, agenda/confirmação abandonada, sessões/detalhe, anomalias pendente/rejeitada, financeiro/relatório e faturas de ambos os meses, parâmetros. Enter foi usado em login, navegação e expansão da memória; foco do conteúdo e links foram conferidos. O retorno ao login após recarregar e o reset da largura foram observados ao terminar.

### Interrupções e controle de repetição

Primeiro teste Vitest restrito falhou no temporário SSR (ENOENT); a mesma suíte executada com permissão adequada passou. Uma tabela parametrizada frontend e uma fixture do teste de feriado foram corrigidas após a primeira verificação. Nenhuma falha exigiu mais de duas correções.

Um lote de navegação foi interrompido após duas capturas móveis. Na continuação, os serviços não respondiam; o cluster **existente**, a API e o Vite foram reiniciados, com janelas ocultas, sem configure/bootstrap/seed/migrations. Saúde voltou a indicar banco disponível. O percurso restante foi retomado a partir das evidências e dos IDs existentes, sem repetir ações de domínio. O índice de capturas foi consolidado a partir do arquivo persistido para evitar perder entradas já coletadas. O verificador offline foi ajustado para chaves compostas, busca por ID e espaço não separável da moeda; a comparação final passou.

## Entrega e apresentação

Roteiro atualizado: [APRESENTACAO.md](APRESENTACAO.md). Execução local: [EXECUCAO.md](EXECUCAO.md). Fonte dos registros finais e evidências identificada por período e ID; conferência de credenciais/tokens e links em [sanitization.json](evidence/resolucao-overview/sanitization.json).

A reserva #9 deixa de ser futura quando seu horário chegar. A ocorrência #1 deve permanecer pendente para a consulta demonstrativa. Novembro fechado é histórico; fechar uma fatura nova antecipadamente agora é recusado. O calendário contém uma data demonstrativa, não todos os feriados. A sessão #1 antiga foi preservada como simulação acelerada; as novas terminaram antes da ingestão.

Sem pendência obrigatória nesta Meta. Aprovação humana de anomalia, atribuição de órfã, integração física, pagamentos, instalação PWA em aparelho e publicação não foram executados nem são alegados como validados. Não houve commit ou envio remoto.
