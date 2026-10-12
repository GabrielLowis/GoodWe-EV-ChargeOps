# Entrega acadêmica — Sprint 02

O enunciado fornecido pede **TXT com o link do repositório do grupo**; código, README atualizado e evidências ficam no repositório. O ZIP limpo é complementar.

## Matriz dos requisitos de entrega

| Requisito | Evidência/procedimento | Situação |
|---|---|---|
| Código-fonte organizado | Pastas e responsabilidades no README | Atendido |
| Descrição da solução | Introdução, tecnologias e limites no README | Atendido |
| Instruções de execução | README e DEVELOPMENT | Documentado; resultado prático em VALIDACAO-ENTREGA |
| Decisões técnicas | README e INTEGRATION | Atendido |
| Justificativa dos desvios da Sprint 01 | Tabela comparativa e fontes no README | Atendido documentalmente; não substitui avaliação funcional |
| Evidências de funcionamento | Seis capturas com legendas, relatório de 12/10 e logs | Presentes; limites de cada validação registrados |
| Português claro, sem abuso de emojis | README principal em português | Atendido |
| Repositório do grupo acessível | GabrielLowis/GoodWe-EV-ChargeOps público | Conferência em VALIDACAO-ENTREGA |
| TXT com link | entrega/ENTREGA.txt, fora do repositório | Gerado ao concluir publicação |
| Commits frequentes/descritivos | Base recebida e mudanças desta preparação | Mensagens descritivas nesta etapa; frequência anterior não comprovada |
| Autoria/compreensão, inclusive de código auxiliado por IA | Decisões, referência da Frente 4 e explicação pelos integrantes | Compreensão de cada integrante depende de verificação humana |
| Escolhas refletindo raciocínio da equipe | Justificativas documentadas | Defesa pela equipe continua necessária |
| Pitch de 5 minutos por aluno na prova presencial | Roteiro abaixo | Gravação/validação presencial pendentes |
| Envio na plataforma da faculdade | Enviar o TXT após conferir o link | Ação do aluno; não realizada nesta preparação |

A matriz trata de documentação/formato. Lógica central e papel estrutural da IA são critérios próprios: os relatórios oferecem evidências sem atribuir nota ou afirmar cobertura integral da Sprint 01.

## Percurso em uma instalação nova

1. Siga o README e [DEVELOPMENT](DEVELOPMENT.md). Em banco vazio, mantenha `SEED_DEMO=true`; consulte `DEMO_PASSWORD` no `.env`. Confirme `/api/saude`, schema e modelo disponíveis.
2. Execute **uma vez** `scripts/simulate.py`, com a API ativa. Anote os IDs impressos de reserva, sessão e fatura. A simulação usa timestamps futuros e pode revisar automaticamente a ocorrência demonstrativa se necessário.
3. Entre como `morador@demo.local`. Localize a reserva e a recarga pelos IDs retornados. Confira origem Simulação, energia, situação e vínculo com a fatura.
4. Abra a fatura e expanda a memória. Use mês/ano do início da sessão em `America/Sao_Paulo`; perto da virada do mês, o período pode diferir da data de preparação. Não presuma valores/IDs das capturas históricas.
5. Consulte a sugestão de horário e abra um rascunho sem confirmar. Explique solar hipotética e custo estimado pela API.
6. Saia e entre como `sindico@demo.local`. Consulte agenda, sessão, fatura e relatório do período retornado; confira carregador, unidade, tarifas e imposto demonstrativos.
7. Consulte Anomalias. Fila vazia é possível: o simulador não garante pendências. A rejeição pela interface está nas capturas de 12/10; não fabricar medições nem afirmar que esses registros vêm no clone.
8. Explique fechamento versus pagamento. Não feche o mês corrente; novas faturas só podem ser fechadas após terminar o período. Sair/recarregar retorna ao login.

As ações persistem no banco de demonstração. Repetir o simulador cria registros e pode recalcular fatura aberta; use o conjunto criado para repetir a apresentação. Para avaliar reserva/cancelamento manual, escolha outra janela livre ainda não iniciada.

No banco dos autores, o [roteiro de 12/10](../frontend/APRESENTACAO.md) preserva o conjunto daquela conferência. Dados locais não são distribuídos como dump; a instalação nova usa seed e simulador existentes.

## Uso de IA e compreensão

Esta preparação foi auxiliada por **Codex/ChatGPT** para inspeção, revisão documental, organização do README, execução isolada, conferência de pacote e publicação Git. Não acrescenta funcionalidades nem modifica regras financeiras/modelos de IA.

Justificativas vêm dos documentos recebidos e do planejamento salvo; não se atribuem decisões inventadas aos integrantes. [USO_DE_IA da Frente 4](../deliveries/frente4/USO_DE_IA.md) descreve aquele módulo e não comprova compreensão dos demais módulos por toda a equipe.

Cada integrante deve explicar reserva → sessão → validação → fatura; regras físicas versus suspeita estatística; fonte das parcelas; autorização por perfil; reconstrução do modelo; e dataset histórico versus simulação do protótipo. Esta preparação não certifica compreensão nem grava o pitch pelo aluno.

## Pitch individual — 5 minutos

| Tempo | Conteúdo e demonstração |
|---|---|
| 0:00–0:40 | Problema da recarga compartilhada; proposta e equipe. |
| 0:40–1:20 | React → FastAPI → PostgreSQL, detector e rateio. Explicar uma decisão técnica e sua motivação. |
| 1:20–2:15 | Morador: reserva, sessão simulada e memória da fatura. Identificar a simulação. |
| 2:15–3:10 | IA: regras/Isolation Forest/LOF na ingestão, suspensão/revisão; mostrar evidência. Explicar limite do baseline. |
| 3:10–4:10 | Síndico: agenda/relatório, Green/Grid, impostos/custo operacional, fechamento sem pagamento. |
| 4:10–5:00 | Desvios, execução, evidências/testes e limitações; mostrar README e repositório. |

O enunciado atual exige **5 minutos por aluno durante a prova presencial obrigatória**, com lançamento de notas condicionado à validação técnica. A Sprint 01 menciona 3 minutos e foi preservada como histórico; o requisito atual prevalece. O roteiro não comprova gravação.

## Arquivos para envio

- **Obrigatório:** `entrega/ENTREGA.txt`, com o endereço real do repositório público.
- **Complementar:** `entrega/EV-ChargeOps.zip`, gerado do commit final.
- **Conferência:** `entrega/manifesto.json`, com commit e SHA-256 do ZIP; não compõe o próprio ZIP.

Confira o link sem autenticação antes de enviar o TXT. Não enviar `.env`, `USUARIOS-TESTE.md`, `.venv`, `.local`, `node_modules` ou `dist`. A saída `entrega/` é ignorada. `deliveries/` acompanha o código como referência original identificada no README.

Funcionalidade: [RESOLUCAO-OVERVIEW](../frontend/RESOLUCAO-OVERVIEW.md). Preparação: [VALIDACAO-ENTREGA](VALIDACAO-ENTREGA.md).
