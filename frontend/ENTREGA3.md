# Entrega 3 — operação do síndico

Frontend implementado em 08/10/2026, conforme `docs/ENTREGAS-FRENTE5.md`. A validação de revisão persistida está pendente por ausência de anomalias na base disponível. A entrega 4 não foi iniciada.

## Implementação

- Menu do síndico: Visão geral, Agenda, Sessões e Anomalias. Navegação por hash, IDs de detalhe, foco no conteúdo e retorno às listas.
- Visão geral com consultas independentes: quantidade total de reservas registradas, sessões e anomalias pendentes. Cada cartão permite atualizar e repetir uma consulta que falhou.
- Agenda do condomínio com moradores, carregador/conector, horários de São Paulo, situação e confirmação de cancelamento de reservas ativas. Reutiliza a lista e a ação da entrega 1.
- Sessões de todos os moradores e detalhe da entrega 2, acrescido de responsável, reserva e forma de atribuição para o síndico. Encerramento, validação e origem simulada permanecem separados.
- Fila de ocorrências com filtros Pendente, Aprovada e Rejeitada. Motivos retornados, detector, score sem interpretação como probabilidade, dados da sessão e revisão registrada.
- Aprovação/rejeição com observação de até 2.000 caracteres. Para aprovação órfã, exige selecionar um morador ativo. Rejeição não atribui responsável; sessões identificadas mantêm sua atribuição.
- Atualização após decisão e após recusa 409 de revisão repetida. Erros da API permanecem visíveis; consultas têm carregamento, vazio, erro e repetição.

Somente rotas existentes: GET reservas, carregadores, sessões/lista e detalhe, usuários, anomalias por status; POST cancelamento de reserva e revisão de anomalia. Como não há GET de detalhe de anomalia, seu endereço por ID busca nas três listas existentes. Nenhuma rota nova foi necessária.

Nenhuma dependência nova, alteração no backend, schema, migrations, IA ou infraestrutura. Nenhuma escrita direta no banco. Nenhuma geração/fechamento de faturas, commit ou publicação.

## Conferência com API e banco reais locais

URL: http://127.0.0.1:5173. API: http://127.0.0.1:8000/docs.

| Cenário | Evidência observada |
|---|---|
| Login do síndico | Menu administrativo com as quatro páginas, sem financeiro |
| Visão geral inicial | 5 reservas, 1 sessão, 0 anomalias pendentes, conforme GETs |
| Agenda | Morador Demo, horários, conector e situações da API |
| Cancelamento administrativo | Criada a reserva #6 pelo POST existente como morador, para 14/10/2026, 10h–11h; cancelada no navegador como síndico, com confirmação e atualização da lista |
| Preservação | Reservas #1–#5 integralmente preservadas, incluindo #3 ativa; única reserva acrescentada foi #6, agora cancelada |
| Sessão #1 | Morador Demo, reserva #1, atribuição pela reserva; 6,2 kWh total, 1 Green e 5,2 Grid; concluída, aprovada para cobrança, Simulação |
| Fila | GETs Pendente/Aprovada/Rejeitada retornaram listas vazias; filtros conferidos no navegador |
| Detalhe inexistente | #anomalias/999999 informa Ocorrência não encontrada e permite repetir a consulta |
| Navegação | Voltar do navegador do detalhe da sessão retorna à lista; links, menu ativo e foco conferidos |
| Celular | Agenda, fila e detalhe de sessão em 390 × 844 px, sem transbordamento horizontal |
| Regressão do morador | Login, lista de reservas, formulário com carregador/disponibilidade, recarga #1 e fatura #1 acessíveis; total continua R$ 4,04 |
| Perfis | Morador não recebe menu administrativo; hash administrativo mostra seu início |
| Sessão em memória | Sair e recarregar retornam ao login |

`evidence/entrega3/api-before.json` e `api-after.json` contêm as respostas HTTP. Comparação integral confirmou preservação de usuários, sessões, anomalias, faturas e todas as reservas anteriores. `reservation-created.json` registra o estado ativo da nova reserva; `verification.json` registra sua situação final cancelada e as verificações de preservação. O resumo passa a ter 6 reservas após esse teste; a contagem inclui canceladas.

Screenshots:

- `01-visao-geral.jpg`: resumo inicial.
- `02-agenda-cancelamento.jpg`: resultado do cancelamento #6 pelo síndico.
- `03-sessao.jpg`: detalhe compartilhado com identificação do responsável.
- `04-fila-vazia.jpg`: fila real sem pendências.
- `05-ocorrencia-inexistente.jpg`: retorno de detalhe indisponível.
- `06-agenda-mobile.jpg`, `07-fila-mobile.jpg`, `08-sessao-mobile.jpg`: conferência em 390 px.

## Build e testes controlados

- `npm --prefix frontend run build`: TypeScript e Vite aprovados na versão final.
- `npm --prefix frontend test`: 12 testes aprovados em 4 arquivos; 6 já existentes e 6 adicionados nesta entrega.
- Novas verificações: aprovação órfã exige residente ativo; observação e atribuição no corpo tipado; rejeição não atribui; sessão identificada mantém morador; POST usa a rota existente e preserva mensagem/status 409; formulário apresenta apenas moradores ativos, limita observação e bloqueia decisão sem sessão/seleção.
- Os testes do formulário usam renderização React com dados controlados, sem navegador ou banco. O teste de 409 usa resposta HTTP controlada. Não comprovam revisão persistida na API real.
- A configuração Vitest passou a incluir `.test.tsx`. Execuções no sandbox tiveram ENOENT em arquivo temporário do runtime; execução fora do sandbox passou com o mesmo código, sem adicionar dependências.
- Suíte de banco não executada; validação real feita pelas rotas HTTP existentes.

## Roteiro para testar

1. Abrir http://127.0.0.1:5173 e entrar como `sindico@demo.local`, com a senha de demonstração local em `DEMO_PASSWORD` do `.env`.
2. Conferir Visão geral: 6 reservas, 1 sessão e 0 pendências, enquanto não houver novos registros.
3. Abrir Agenda. Conferir a reserva #3 ativa e #6 cancelada. Para repetir cancelamento, criar uma nova reserva como morador, sair, entrar como síndico e cancelar somente essa reserva de teste.
4. Abrir Sessões → Ver sessão #1. Mostrar responsável, origem simulada, energias e diferença entre conclusão e validação. Voltar para a lista.
5. Abrir Anomalias e selecionar as três situações. A base atual mostra ausência de ocorrências.
6. Quando houver uma ocorrência pendente: abrir o detalhe, conferir motivos e sessão, selecionar Aprovar/Rejeitar, escrever observação e Confirmar revisão. Aprovação sem responsável exige morador ativo. Voltar à fila, selecionar a situação correspondente e conferir a revisão. O detalhe da sessão deve refletir a validação atualizada.
7. Sair da conta. Entrar como `morador@demo.local` para conferir reservas, recargas e a fatura existente. Recarregar exige novo login.

Se os serviços estiverem parados, seguir `docs/DEVELOPMENT.md`. Não executar bootstrap/migrations ou o simulador completo para repetir esta conferência: não são necessários para consultas e cancelamento; o roteiro do simulador inclui ações financeiras fora desta entrega.

## Pendências e limites

**Pendente: validar aprovação, rejeição e atribuição órfã persistidas com a API real.** Os três GETs de anomalias retornaram zero registros. A base contém somente a sessão #1 já aprovada, sem anomalia. Não foram inseridas medições/sessões artificiais nem modificados registros anteriores para criar esse cenário. Não existe incompatibilidade de contrato que exija mudança de backend; é uma limitação do conjunto de dados. Uma ocorrência adequada precisa estar disponível para concluir essa demonstração.

Revisão concorrente (409), falha de rede e falha parcial do resumo não foram provocadas nos serviços reais. Aprovação/rejeição e seleção de morador foram verificadas em testes controlados conforme descrito. Celular foi conferido por viewport, sem aparelho físico ou instalação PWA.

Financeiro administrativo, consultas de parâmetros e fechamento da apresentação permanecem exclusivamente na entrega 4. Telemetria física não está conectada.
