# Apresentação — percurso de 8–10 minutos

> Roteiro do banco existente dos autores. Para avaliar um clone com banco novo, use [ENTREGA-ACADEMICA](../docs/ENTREGA-ACADEMICA.md#percurso-em-uma-instalação-nova); IDs e datas abaixo pertencem ao conjunto local de 12/10.

Conferido em **12/10/2026, fuso de São Paulo**, após a resolução D01–D05. Abra http://127.0.0.1:5173 e confira http://127.0.0.1:8000/api/saude. Comandos: [EXECUCAO.md](EXECUCAO.md). Resultados e evidências atuais: [RESOLUCAO-OVERVIEW.md](RESOLUCAO-OVERVIEW.md). A validação de 11/10 permanece como registro histórico em [VALIDACAO-FINAL.md](VALIDACAO-FINAL.md).

## História dos registros

- Morador Demo, usuário #2, unidade A-101; Síndico Demo, usuário #1. Contas `morador@demo.local` e `sindico@demo.local`; use a senha local existente sem exibi-la à equipe.
- HCA01, carregador #1, conector 1, 7 kW. Reserva concluída #1 → recarga #1 aprovada → item #35 → fatura #1 de outubro, **R$ 4,04**. Origem `simulator`: 6,2 kWh, sendo 1 Green e 5,2 Grid.
- Reserva #3, 09/10, 13h–18h: agora `no_show`, reconciliada como **falta simulada**, sem prova de ausência física. Não bloqueou o morador. Não há processamento automático de faltas.
- Reserva #9: 13/10, 09h–10h. É a única reserva nova desta Meta. Cancelamento disponível somente antes das 09h. Se a demonstração ocorrer durante/depois da janela, a interface explica o horário e remove a ação; não criar outro cenário para reproduzir o destaque.
- Anomalia #1 / sessão #2 permanece pendente; anomalia #2 / sessão #3 foi rejeitada pela interface em 12/10 às 13h38, com observação simulada. Ambas sem responsável/reserva, com **zero energia**, duração de um minuto e origem `simulator`; nenhuma gera cobrança.
- Fatura #2, novembro, fechada e zerada: **teste histórico de fechamento anterior à regra nova**, integralmente preservado. Continua acessível, identificada como período futuro em outubro. Seu estado não comprova pagamento.
- Feriado cadastrado: 12/10/2026, “Feriado de demonstração acadêmica”. A configuração atual aplica fora de ponta aos feriados cadastrados; essa única data não constitui um calendário real completo.

## Percurso pelos dois perfis

| Tempo | Ação e explicação |
|---|---|
| 0:00–1:00 | Entrar como morador. Em outubro, o início destaca fatura #1, R$ 4,04; a reserva #9 aparece como próxima somente enquanto seu início estiver no futuro. |
| 1:00–2:00 | Minhas reservas: #9 antes do histórico; #3 com “Não compareceu”. Explicar cancelamento antes do início. Se abrir a confirmação de #9, abandoná-la para preservar o cenário. |
| 2:00–3:00 | Sugestão de horário: HCA01, 6,2 kWh, 3,3 kW. Consultar e abrir o rascunho de reserva sem confirmar. Horários são dinâmicos; solar é hipótese, valores estimados vêm da API. Em 12/10, a janela ocupada de amanhã é 09h–10h. |
| 3:00–4:15 | Minhas recargas → #1. Mostrar reserva #1, Simulação e “Aprovada para cobrança”. Seguir o link da fatura de outubro; expandir memória e usar o link inverso da recarga. Aprovação, faturamento, fechamento e pagamento são conceitos distintos. |
| 4:15–5:00 | Lista de faturas → novembro/#2. Explicar valor zero e fechamento histórico antecipado; retornar a outubro. Nenhum recalculo/fechamento necessário. |
| 5:00–6:00 | Sair, entrar como síndico. Visão geral → agenda → sessões; #9 e a sessão #1 com seus vínculos. As sessões #2/#3 são conexões simuladas sem recarga e sem identificação. |
| 6:00–7:15 | Anomalias → Pendente → #1, consultar motivos e formulário sem salvar. Rejeitada → #2, mostrar autor, horário e observação persistida. A revisão já aconteceu; não rejeitar novamente nem atribuir dono/aprovar #1. |
| 7:15–8:15 | Financeiro → outubro → fatura #1. R$ 4,04, 6,2 kWh e parcelas; fechamento desabilitado até **01/11/2026 00h de São Paulo**. O relatório financeiro coloca as duas sessões órfãs em “Sem morador identificado”; os grupos têm prioridade exclusiva, não são a fila de anomalias. |
| 8:15–9:00 | Cadastros e parâmetros: carregador, unidade, tarifa e imposto de demonstração. Mostrar a explicação de feriados cadastrados. O cadastro do feriado é comprovado no relatório, não há editor/lista de feriados nessa tela. |
| 9:00–9:30 | Mostrar disposição em 390 px, se necessário. Sair ou recarregar demonstra retorno ao login, pois a autenticação permanece em memória. |

Parcelas de outubro preservadas: Green R$ 0,30; Grid R$ 3,38; ociosidade R$ 0,00; subtotal R$ 3,68; imposto R$ 0,18; custo operacional R$ 0,18; total R$ 4,04. A interface apresenta campos da API; o motor financeiro continua sendo a fonte do cálculo.

## Perguntas previsíveis e limites

“Por que novembro está fechado?” Foi um teste anterior à regra de fechamento após o período. Mantivemos o histórico e bloqueamos novos fechamentos antecipados.

“Por que a anomalia rejeitada está em sem morador no financeiro?” O relatório agrupa primeiro pela falta de atribuição. A fila de anomalias registra a decisão de revisão; o saldo entregue/faturado permanece 6,2 kWh e as duas sessões novas têm zero energia.

“Por que a recarga #1 foi registrada antes de terminar?” O registro antigo veio de simulação acelerada; foi preservado. Os dois cenários desta Meta terminaram antes da ingestão e não representam carregamento físico.

Não há telemetria física GoodWe/SEMS/Modbus nem pagamentos. Instalação PWA em aparelho continua sem comprovação; a validação histórica do preview e contingência está em VALIDACAO-FINAL. A resolução atual verificou navegação integrada local em desktop/390 px e build, sem ampliar essa afirmação.

Para apresentar, consulte os registros existentes. Não executar simulador geral, geração/recalculo, fechamento ou novas revisões apenas para repetir evidência. O roteiro depende do relógio real; não alterar datas para manter artificialmente uma reserva futura.