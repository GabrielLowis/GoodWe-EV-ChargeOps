# Entrega 4 — financeiro e apresentação

Implementada e conferida entre 08 e 09/10/2026. Reutiliza autenticação, layout, listas, mensagens e detalhe da fatura. Sem novas dependências ou alterações de backend, schema, migrations, IA, infraestrutura ou entregas originais.

Instruções: `frontend/EXECUCAO.md`. Roteiro: `frontend/APRESENTACAO.md`.

## Implementação concluída

- Financeiro do síndico com seleção de mês/ano civil entre 2000 e 2100, faturas por período e geração/recalculo para o conjunto de moradores elegíveis.
- Confirmação simples antes da geração. A API mantém faturas fechadas e recalcula as abertas; resultados e erros são apresentados, e lista/relatório são atualizados.
- Detalhe da entrega 2 compartilhado: parcelas, consumo, itens, critérios e observações. Links para a sessão usam a área correspondente ao perfil.
- Fechamento individual com identificação, período, total e confirmação de que não poderá recalcular. Depois da ação, consulta atualizada e situação Fechada. Morador segue apenas com consulta.
- Relatório mensal com total, parcelas, energia faturada/registrada, distribuição dos valores, sessões por situação e lançamentos anteriores, usando os campos retornados. Campos ausentes aparecem como Não informado; não são transformados em zero. Não há cálculo financeiro no frontend nem indicação de pagamento recebido.
- Consulta administrativa de carregadores, unidades, versões de tarifas, preços Green/Grid, janelas, ociosidade, custo operacional e impostos. Blocos consultam independentemente e permitem repetição de erro.
- Manifest com ID, escopo, descrição, ícones PNG 192/512 e maskable. Ícones derivam do símbolo vetorial existente. Página offline autossuficiente com visual compartilhado e retorno ao login quando o serviço volta.

Rotas utilizadas: GET `/api/faturas`, `/api/faturas/{id}`, `/api/relatorios/arrecadacao`, `/api/carregadores`, `/api/unidades`, `/api/tarifas`, `/api/impostos`, `/api/usuarios`; POST `/api/faturas/gerar` e `/api/faturas/{id}/fechar`. Nenhum novo contrato.

## Resultados dos testes

- `npm --prefix frontend test`: **22 testes aprovados em 7 arquivos**.
- `npm --prefix frontend run build`: **TypeScript e Vite aprovados**, incluindo os testes TS/TSX.
- Novas verificações pontuais: período civil e limites, preço unitário com quatro casas, campos ausentes de relatório, acesso ao fechamento por papel/situação, links do detalhe compartilhado, instalação do cache de contingência e navegação online/offline do worker.
- Testes de PWA em VM e de componentes com renderização React são controlados; a prova de navegação offline no navegador real está separada abaixo.
- Não executada suíte de banco; nenhuma suíte foi apontada ao banco de desenvolvimento. Integração feita por HTTP, com o banco local existente.

| Entrega / cenário | Resultado efetivamente conferido |
|---|---|
| 1 — login e perfis | Contas do síndico/morador abrem menus corretos; sair e recarregar retornam ao login |
| 1 — reserva | Nova reserva #7 confirmada no navegador, depois cancelada pelo morador; anteriores #1–#6 preservadas |
| 1 — conflito | POST repetindo o intervalo ativo de #7 recusado com 409, Janela já reservada, sem criar outro registro |
| 2 — sugestão | HCA01, 6,2 kWh, 3,3 kW: janela 09/10, 11h–12:52:43.636364, estimativa R$ 2,10, comparação R$ 4,43, economia R$ 2,33 na consulta registrada |
| 2 — transporte do intervalo | Reserva #7 corresponde aos instantes UTC da sugestão, incluindo microsegundos; conferido por HTTP |
| 2 — sessão e fatura | Sessão #1 com 6,2 kWh (1 Green + 5,2 Grid), simulada/aprovada; fatura #1 aberta com parcelas e total R$ 4,04 |
| 3 — operação | Agenda e detalhe administrativo da sessão acessíveis; filtros de anomalias retornam vazio; cancelamento do síndico já validado na entrega 3, sem novo cancelamento administrativo nesta etapa |
| 3 — revisão persistida | **Não validada:** zero anomalias na API; seleção/decisão/409 continuam verificadas em testes controlados, sem criar medições artificiais |
| 4 — recalculo | Geração do conjunto em outubro recalculou a fatura #1 e manteve período, consumo, parcelas, total e memória; itens podem receber novo ID ao recalcular |
| 4 — geração e fechamento | Fatura #2 de novembro gerada pela API em R$ 0,00, sem consumo, e fechada no navegador; cancelar a confirmação com Manter aberta também foi conferido |
| 4 — imutabilidade pública | Nova geração do conjunto de novembro retornou a fatura #2 ainda fechada; comparação integral da resposta confirmou preservação |
| 4 — relatório | Outubro: R$ 4,04, 6,2 kWh, 1 fatura/0 fechadas. Novembro: R$ 0,00, 0 kWh, 1 fatura/1 fechada. Comparado aos GETs |
| 4 — parâmetros | Dados reais dos GETs, incluindo HCA01/7 kW, A-101, três faixas, janelas, ISS 5% e base fictícia identificada |
| Responsivo | Financeiro, parâmetros e detalhe fechado em 390 px sem transbordamento; desktop conferido. Evidência da área do morador e operação em 390 px também preservada nas entregas 1–3 |
| Build de produção | Preview 4173 com login e financeiro integrados à API 8000 |
| Contingência real | Parado somente o preview criado para a validação; recarregar exibiu Sem conexão pelo worker. Preview restaurado e Tentar novamente voltou ao login |

As recomendações são dinâmicas. A comparação HTTP da sugestão foi realizada com os mesmos parâmetros antes de confirmar a reserva, e corresponde ao intervalo observado no formulário. Não é uma resposta fixa futura.

## Preservação e ambiente

`evidence/entrega4/api-before.json` e `api-after.json` registram consultas reais. `verification.json` contém os resultados e healthcheck final: banco OK, migration `0001_schema_inicial`, modelo `v1.0.0`.

Comparações confirmaram reservas anteriores, sessão, usuários e parâmetros intactos. Outubro permaneceu aberto para a apresentação; novembro é um novo registro de demonstração fechado sem consumo. Não houve inserção de sessão nem anomalia. Hashes de 210 arquivos existentes de backend, IA, scripts, infraestrutura e entregas de referência permaneceram iguais.

Durante o percurso, o processo local do PostgreSQL foi interrompido; login exibiu Banco de dados indisponível. O serviço existente foi reaberto com o helper original, sem bootstrap/migrations/recriação de banco. Após a recuperação, login, leituras e comparação de registros passaram. O preview foi reiniciado após a prova de contingência; serviços estavam ativos ao finalizar.

Outras evidências: `reservation-active.json`, `reservation-conflict.json`, `recommendation.json`, `invoice-closed-before-regenerate.json` e screenshots numerados `01`–`16`. Os arquivos `07`–`09` são as capturas efetivas de 390 px; `15` é a contingência real. Nenhum token ou senha foi salvo nesses registros.

## Pendências e limites

1. **Revisão de anomalia persistida com API real:** falta uma ocorrência adequada na base. Frontend implementado, testes controlados aprovados; não declarar essa demonstração concluída. Não há incompatibilidade de contrato identificada que exija alterar backend.
2. **Instalação PWA em aparelho:** manifest, ícones, registro do worker e contingência foram conferidos; o navegador disponível não forneceu fluxo de instalação. Instalação/abertura standalone em dispositivo físico não testadas.
3. Multimorador, faturas com entradas tardias, falhas financeiras concorrentes e interrupção real da internet não foram provocados nesta base. A contingência foi provada pela indisponibilidade do preview, que causa falha real na navegação.

Telemetria física, pagamentos e implantação externa continuam fora do escopo. A implementação das quatro entregas está disponível; o aceite prático de revisão de anomalia permanece pendente de dados.
