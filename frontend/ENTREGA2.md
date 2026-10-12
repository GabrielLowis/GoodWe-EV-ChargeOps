# Entrega 2 — área do morador

Implementada e validada em 08/10/2026, conforme o pacote principal de `docs/ENTREGAS-FRENTE5.md`.

## Funcionalidades concluídas

- Menu do morador com Minhas recargas, Minhas faturas e Sugestão de horário, mantendo o visual e a autenticação da entrega 1.
- Listagem e detalhe de recargas com Green/Grid, origem, horários e situações separadas de encerramento e validação para cobrança. Origem `simulator` identificada como Simulação.
- Listagem e detalhe de faturas por período civil, parcelas e memória de cálculo retornadas pela API. Itens expansíveis com regra, tarifa, explicações, observações e vínculo ao detalhe da recarga. Entradas tardias e registros não incluídos são apresentados quando informados.
- Sugestão consultada após envio de carregador, energia e potência. Custos/economia e premissas são exclusivamente os retornados pela API. Geração solar hipotética identificada.
- Preenchimento da reserva por rascunho em memória, sem agendamento automático. Conversão visual para São Paulo e preservação dos instantes originais, inclusive frações de segundo, até edição dos campos.
- Início com próxima reserva ativa futura, três recargas recentes, última fatura por período e perfil. Cada bloco tem consulta e tratamento de falha independentes.
- Estados de carregamento, ausência de dados, erros e repetição da consulta. Rotas de detalhe por hash com ID, indicação do menu ativo, foco e retorno à lista.

Nenhuma dependência nova. Nenhuma rota ou contrato público foi alterado. Detalhes de recarga/fatura foram separados para reutilização futura pelo síndico, sem acrescentar funções administrativas nesta entrega.

## Evidência prática — API e banco locais existentes

O frontend foi conferido no navegador em http://127.0.0.1:5173, usando a conta de demonstração de morador. API/banco conectados, migration `0001_schema_inicial`.

| Cenário | Resultado observado |
|---|---|
| Início do morador | Nome/unidade, reserva #3, sessão #1 e fatura #1 provenientes da API |
| Recarga #1 | 6,200 kWh: 1,000 Green e 5,200 Grid; concluída, aprovada para cobrança, origem simulada |
| Fatura #1 | Outubro/2026, aberta; Green R$ 0,30, Grid R$ 3,38, ociosidade R$ 0,00, subtotal R$ 3,68, impostos R$ 0,18, custo operacional R$ 0,18, total R$ 4,04 |
| Memória de cálculo | Item expandido; regra, explicações e parâmetro tributário fictício retornados pelo backend |
| Sugestão | HCA01, 6,2 kWh, 3,3 kW: 09/10/2026, 11:00–12:52:43.636364; estimativa R$ 2,10, custo atual estimado R$ 4,43, economia estimada R$ 2,33 naquele momento |
| Alteração dos parâmetros | Resultado anterior limpo; nova consulta necessária |
| Usar este horário | Formulário preenchido, com escolha/confirmação do conector; mensagem de que nada foi reservado ainda |
| Confirmação | Reserva #5 criada pela API; horário persistido corresponde exatamente à sugestão, incluindo microsegundos |
| Cancelamento | Reserva #5 cancelada pela API; registros anteriores preservados |
| Intervalo já reservado | Tentativa manual de 09/10, 13h–18h recusada por conflito com a reserva #3, sem alterar essa reserva |
| Sugestão inválida | 200 kWh a 3,3 kW recusados pela API por exceder 12 horas; erro e ação de tentar novamente exibidos |
| Fatura inexistente | Detalhe #999999 mostra Registro não encontrado e Tentar novamente |
| Navegação | Botão Voltar do navegador retorna à lista de recargas; links de detalhe/lista e menus conferidos |
| Perfil do síndico | Área básica da entrega 1 preservada; novos menus do morador não exibidos |
| Recarregamento | Retorno ao login, conforme o contrato de sessão em memória |
| Largura de 390 px | Início, memória da fatura, sugestão e reserva conferidos sem transbordamento horizontal |

As sugestões são dinâmicas: esses horários e valores registram a consulta realizada, não são respostas fixas para futuras demonstrações.

`evidence/entrega2/api-before.json` e `api-after.json` contêm respostas HTTP de demonstração antes/depois. Comparação integral confirmou sessões/faturas inalteradas e reservas #1–#4 preservadas. `verification.json` registra a reserva #5 cancelada e a preservação do intervalo. `reserva-api.json` registra o retorno durante o estado ativo. Os screenshots retratam as etapas respectivas, não somente o estado final.

## Build e testes

- `npm --prefix frontend run build`: TypeScript e build Vite aprovados na versão final.
- `npm --prefix frontend test`: seis testes aprovados, em dois arquivos. Três testes existentes de HTTP e três novos testes pontuais de fuso/mudança de dia, intervalo com segundos/fração e mês civil da fatura.
- A primeira execução do Vitest teve um ENOENT em arquivo temporário do runtime. A repetição do mesmo comando passou sem mudanças na configuração da suíte.
- Não foi executada a suíte de banco. A verificação de integração utilizou as rotas HTTP existentes; sem acesso direto ao banco, bootstrap ou migrations.

## Roteiro para conferir

1. Abrir http://127.0.0.1:5173 e entrar com `morador@demo.local`, usando a senha local em `DEMO_PASSWORD`.
2. Conferir o início e abrir Minhas recargas → Ver recarga #1. Mostrar origem simulada, Green/Grid e a diferença entre conclusão e validação.
3. Abrir Minhas faturas → Ver fatura #1. Conferir R$ 4,04 e expandir Recarga #1 para explicar as parcelas.
4. Abrir Sugestão de horário, selecionar HCA01 e informar 6,2 kWh a 3,3 kW. Consultar e ler as premissas.
5. Clicar Usar este horário. Conferir data, início, fim e conector. Somente Confirmar reserva envia o agendamento.
6. Conferir a nova reserva na lista e cancelar apenas essa reserva criada para a demonstração. Preservar os agendamentos anteriores.
7. Sair e entrar como síndico para mostrar que sua área básica segue disponível. Recarregar exige novo login.

Com os serviços parados, seguir `docs/DEVELOPMENT.md`. Não reiniciar o ambiente quando já estiver em execução.

## Limites verificados

Sem impedimento observado no percurso principal. A base disponível possui um carregador/conector, uma sessão aprovada e uma fatura aberta. Não foram fabricados registros para testar listas vazias, faturas fechadas, sessões suspensas, entradas tardias ou itens não incluídos; esses estados têm apresentação implementada, mas não evidência prática nesta base. Não foram interrompidos os serviços para forçar falhas de rede.

A conferência de celular foi por viewport, sem aparelho físico ou instalação PWA. Não houve geração/fechamento de faturas, alteração de código do backend, schema, migrations, IA, infraestrutura, commit ou publicação. Operação administrativa e financeiro continuam nas entregas 3–4.
