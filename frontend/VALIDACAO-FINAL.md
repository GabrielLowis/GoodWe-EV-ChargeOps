# Validação final — EV ChargeOps

> Registro histórico de 11/10/2026, preservado. A validação funcional posterior está em [RESOLUCAO-OVERVIEW](RESOLUCAO-OVERVIEW.md); a preparação acadêmica está em [VALIDACAO-ENTREGA](../docs/VALIDACAO-ENTREGA.md).

Conferência em **11/10/2026**, para apresentação acadêmica em **13/10/2026**. Trabalho limitado ao frontend e documentação, preservando as quatro entregas. Evidências atuais em [evidence/validacao-final](evidence/validacao-final/); registros ENTREGA1–4 e suas pastas de evidência permanecem como histórico.

## Checklist dos cinco pontos

- [x] **1. Execução e roteiro:** comandos e URLs verificados; roteiro de 8–10 minutos pelos dois perfis, contas sem senha exposta, horários futuros, fatura com consumo separada da fatura zero. Corrigidos somente trechos desatualizados de implementação em README, AGENTS e FRONTEND, mantendo regras.
- [x] **2. Conferência da fila encerrada:** API e navegador retornaram zero pendentes, aprovadas e rejeitadas. Aprovação, rejeição e atribuição órfã **não validadas — cenário indisponível**. Revisão persistida continua pendente da entrega 3. Nenhuma sessão, medição ou anomalia foi criada para forçar cenário.
- [x] **3. Acabamento pequeno:** botão Mostrar/Ocultar senha acessível, `type=button`, `aria-controls` e `aria-pressed`, sem envio do formulário. Desktop de 1280 px, largura de 390 px e teclado conferidos nas telas do percurso, sem transbordamento horizontal observado.
- [x] **4. Único extra, dashboard:** contagens preservadas; até três reservas ativas com início futuro em ordem crescente e até três sessões por início mais recente. Atalhos para agenda/detalhes funcionam. Reutiliza as consultas existentes; reservas, sessões e fila têm carregamento, erro e repetição independentes.
- [x] **5. Regressão e evidências:** build aprovado, 26 testes em 8 arquivos aprovados; percursos na API local e navegador, preservação e preview/PWA conferidos. Instalação física não comprovada.

O ponto 2 atende ao critério condicional de encerrar a conferência com a limitação documentada; isso não comprova uma revisão real. Nenhum impedimento obrigatório dos cinco pontos permaneceu.

## Melhorias implementadas e validação controlada

Alterações de interface em `src/pages/LoginPage.tsx`, `src/pages/ManagerPage.tsx` e `src/styles.css`, mantendo o visual existente, autenticação em memória e contratos. Os botões de atualização das contagens receberam nomes acessíveis específicos. Nenhuma nova dependência, tela, filtro ou cálculo financeiro.

Quatro testes pontuais do dashboard em `src/pages/ManagerPage.test.tsx`: exclusão de reservas passadas/canceladas/já iniciadas, ordenação/limite de três sem alterar as listas recebidas, links de sessão e independência dos estados de erro/carregamento/vazio. São dados controlados e renderização React; não são evidência de registros reais nem de falha parcial provocada nos serviços.

`npm --prefix frontend run build`: TypeScript e Vite v8.3.3 aprovados; 34 módulos transformados. `npm --prefix frontend test`: **26/26 aprovados, 8/8 arquivos** ([tests.txt](evidence/validacao-final/tests.txt)). A primeira execução restrita falhou com ENOENT em arquivos temporários SSR do Vitest; o mesmo comando fora do sandbox passou, sem mudança de configuração ou dependências. Não foi executada suíte de banco.

## Ambiente e URLs atuais

| Endereço | Resultado atual |
|---|---|
| http://127.0.0.1:5173 | HTTP 200; frontend de desenvolvimento integrado |
| http://127.0.0.1:4173 | HTTP 200; preview do novo build, dois perfis conferidos |
| http://127.0.0.1:8000/docs | HTTP 200; documentação da API |
| http://127.0.0.1:8000/api/saude | HTTP 200; banco OK, schema `0001_schema_inicial`, modelo `v1.0.0` |

Serviços inicialmente parados. Iniciados somente o cluster previamente existente (PG_VERSION confirmado), uvicorn e Vite, usando os caminhos dos scripts originais. Não executados configure, criação de bancos, bootstrap, migrations, seeds ou simulador. API, banco, Vite e preview estavam ativos ao encerrar. Instruções atuais: [EXECUCAO.md](EXECUCAO.md).

## Percursos com API real local

| Cenário | Resultado e evidência |
|---|---|
| Login, perfis e saída | Morador/resident e síndico/manager abriram menus correspondentes; saída por teclado retornou ao login. Contas existentes consultadas por HTTP. |
| Recarregar | Os dois perfis retornaram ao login, preservando o contrato de token em memória. |
| Senha e teclado | Com texto de amostra, Espaço mostrou e Enter ocultou; tipo alternou para text/password e `aria-pressed` refletiu estado, mantendo a tela de login. Tab percorreu e-mail → senha → alternância → envio, com foco visível. Nenhuma senha foi salva nas evidências. |
| Sugestão | HCA01, 6,2 kWh a 3,3 kW: consulta atual sugeriu **12/10/2026, 11:00–12:52:43.636364 −03:00**, R$ 2,10, comparação R$ 4,43 e economia estimada R$ 2,33. Baseline com geração solar hipotética; resposta dinâmica. |
| Transporte e criação | Única reserva nova: **#8**, criada no navegador. HTTP confirmou equivalência exata à sugestão, inclusive microssegundos. POST respondeu 201. |
| Conflito | Formulário com a mesma janela foi recusado com HTTP 409 e mensagem compreensível. Nenhuma segunda reserva criada. Preenchimento automatizado de date/time exigiu eventos reais de teclado; a primeira tentativa só mostrou validação local, sem POST. |
| Dashboard e atalhos | Antes da criação: 7 reservas, 1 sessão, 0 pendências; nenhuma ativa futura. Com #8 ativa: 8 reservas, #8 no bloco futuro, sessão #1 no bloco recente. Reserva passada #3 excluída. Links da reserva para agenda e da sessão para #sessoes/1 conferidos por teclado. Após cancelamento: 8 registros e bloco futuro vazio. |
| Cancelamento | Somente #8 cancelada pelo morador com confirmação; POST respondeu 200. Reservas anteriores #1–#7 preservadas integralmente. |
| Sessão | #1: 6,2 kWh, 1 Green + 5,2 Grid, concluída, aprovada, origem simulator. Conferida pelos dois perfis contra HTTP; não comprova telemetria física. |
| Fatura com consumo | #1 de outubro aberta: Green R$ 0,30, Grid R$ 3,38, ociosidade R$ 0,00, subtotal R$ 3,68, impostos R$ 0,18, operacional R$ 0,18, total R$ 4,04. Memória expandida por teclado e parcelas comparadas à API. |
| Recalculo | Uma geração do conjunto de outubro pela interface, com confirmação e HTTP 200. #1 continua aberta, com mesmas energias, parcelas, total e memória. Somente IDs internos de itens podem mudar no recalculo; comparação econômica desconsiderou esse ID. |
| Fechamento | Apenas consultada #2 de novembro já fechada, zero consumo/total. Resposta integral preservada. Ação de fechar usa **evidência histórica de 08–09/10**, em `evidence/entrega4/04-confirmacao-fechamento.jpg`, `05-fatura-fechada.jpg` e `verification.json`; não foi repetida nem criado outro período. |
| Relatório | Outubro: 1 fatura, 0 fechadas, R$ 4,04, 6,2 kWh. Novembro: 1 fatura fechada, R$ 0,00, 0 kWh. Telas e GETs comparados; não são pagamentos. |
| Parâmetros | Consultados HCA01/7 kW, A-101, tarifa vigente com três faixas/janelas e ISS 5% com base fictícia identificada. Consultas administrativas existentes. |
| Agenda/fila | Horários e estados da agenda conferidos. Os três filtros da fila mostram vazio, conforme HTTP. |

## Anomalias — resultado de cada cenário

| Cenário | Resultado | Evidência |
|---|---|---|
| Aprovação com observação | **Não validado — cenário indisponível** | GET pending_review: 0; screenshot 01 |
| Rejeição com observação | **Não validado — cenário indisponível** | GET pending_review/rejected: 0; screenshots 01/03 |
| Atribuição órfã ao aprovar | **Não validado — cenário indisponível** | Fila pendente vazia; sessão #1 já atribuída por reserva e aprovada |

GET approved também retornou 0 (screenshot 02). Não houve decisões sobre registros de origem desconhecida. Os testes controlados preservados da entrega 3 não comprovam revisão persistida. Não continuar procurando meios de fabricar dados para esta meta.

## Layout, teclado e PWA

Login, início do morador, sugestão, formulário/lista de reservas, listas/detalhes de sessões e faturas, dashboard, agenda, fila, financeiro e parâmetros foram conferidos em desktop e/ou seus componentes compartilhados em 390 px. [browser-checks.json](evidence/validacao-final/browser-checks.json) registra largura, scrollWidth, título e foco; nenhum registro apresentou scrollWidth maior que a largura. Screenshots móveis mostram formulário, memória expandida, parâmetros, lista e os novos blocos do dashboard. Não surgiu impedimento adicional que justificasse redesenho.

Controles principais acionados por Enter/Espaço: login, alternância de senha, menus, links do dashboard, confirmação de reserva/conflito/cancelamento, geração e expansão da memória. Navegação leva foco a main-content. A conferência não representa auditoria completa de leitor de tela.

Preview atual: login dos dois perfis e dashboard funcionando com a API. Manifest, ícones PNG 192/512/maskable, sw.js e offline.html retornaram HTTP 200. Depois de visita online, foi parado **somente o preview identificado**; recarregar exibiu **Sem conexão**, comprovando a contingência do worker no navegador. Preview restaurado, Tentar novamente voltou ao login. Screenshots 25–28 e [pwa-browser.json](evidence/validacao-final/pwa-browser.json).

**Não comprovado:** instalação/abertura standalone em aparelho físico, indisponibilidade real da internet no aparelho, operação offline das APIs, telemetria GoodWe/SEMS/Modbus e pagamentos. A contingência é um aviso de indisponibilidade, sem reservas/faturas offline. Sem infraestrutura adicional para testar instalação.

## Preservação e índice das evidências

- [api-before.json](evidence/validacao-final/api-before.json) e [api-after.json](evidence/validacao-final/api-after.json): consultas atuais dos dois perfis, saúde, listas/detalhes e relatórios, sem tokens/senhas.
- [preservation.json](evidence/validacao-final/preservation.json): #1–#7 preservadas; somente #8 acrescentada/cancelada; sessão e fatura fechada intactas; outubro aberto e economia/memória preservadas; usuários, parâmetros, anomalias e relatórios intactos.
- [recommendation.json](evidence/validacao-final/recommendation.json), reservation-draft.json, reservation-active.json e [reservation-transport.json](evidence/validacao-final/reservation-transport.json): equivalência dos instantes.
- [http-actions.log](evidence/validacao-final/http-actions.log): únicas ações de domínio, 201 criação, 409 conflito, 200 recalculo e 200 cancelamento #8. Nenhum POST de fechamento, sessão ou revisão.
- [protected-files-verification.json](evidence/validacao-final/protected-files-verification.json): SHA256 de **224 arquivos existentes** de backend, IA, scripts, infraestrutura, dados e deliveries sem alteração.
- tests.txt, build.txt, urls-pwa-http.json e verification.json: resultados e resumo estruturado. Screenshots 01–28: filas, larguras móveis, reserva/conflito/dashboard, faturas e PWA.

Repositório já estava com os arquivos não rastreados na abertura; nenhum arquivo foi preparado para commit, commitado ou publicado. Dados locais foram alterados somente pelas quatro ações HTTP autorizadas. Arquivos operacionais de PID/log em .local identificam os serviços iniciados; não são alteração de infraestrutura/código.

## Conferência curta

1. Abra 5173 ou 4173; entre como morador, teste Mostrar/Ocultar senha e consulte recarga #1 e fatura #1 de outubro.
2. Saia, entre como síndico; confira dashboard (8 registros, 1 sessão, 0 pendências), agenda, atalho da sessão, fila vazia e parâmetros.
3. Financeiro: outubro aberto com R$ 4,04 e novembro fechado com R$ 0,00. Para roteiro completo, siga [APRESENTACAO.md](APRESENTACAO.md); não feche outubro nem crie outro período para repetir fechamento.
