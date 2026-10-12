# Uso de Inteligência Artificial — Frente 4

O briefing da Sprint 2 permite o uso de ferramentas de IA no desenvolvimento, desde que o código seja compreendido e autoral e que as decisões reflitam o raciocínio da equipe. Este documento registra, de forma transparente, como a IA foi usada na Frente 4 e o que foi decidido pela equipe.

## Ferramentas e usos

| Ferramenta | Como foi usada |
|---|---|
| **Claude (chat)** | Tutor durante todo o desenvolvimento: explicação de conceitos de Python e de ML, orientação passo a passo, depuração de erros e revisão de cada trecho escrito. A maior parte do código foi escrita pelo integrante com essa orientação; alguns trechos foram sugeridos prontos pela IA e depois revisados e testados (as regras de potência, capacidade e atribuição, a função que agrega as regras, o script de treino, a leitura dos CSVs e a criação das anomalias de avaliação). Também gerou os rascunhos do README e do DECISOES.md, revisados e ajustados pelo integrante. |
| **Claude Code** | Três revisões do código pronto: acréscimo de comentários e docstrings (sem alterar lógica) e um relatório de bugs, inconsistências e pontos frágeis. As correções foram decididas e aplicadas pelo integrante, uma a uma. |
| **Extensão de IA para navegador** | Extração das 225 sessões de recarga da plataforma SEMS+, em modo somente leitura, a partir de instruções detalhadas. Os dados foram validados depois da extração, o que revelou um erro de leitura no campo green em 35 sessões, corrigido e documentado. |

## Como o uso foi conduzido

- **Nenhum código foi aceito sem ser entendido.** Cada função passou por explicação linha a linha, teste no terminal e teste automatizado antes do commit.
- **Os resultados da IA foram conferidos contra os dados reais.** Várias sugestões iniciais foram corrigidas quando o dado real mostrou outra coisa: a potência média do carregador (2,3 kW, e não 3,0 kW como estimado no início), a tolerância da regra de atribuição (que gerava falso alarme em sessões pequenas) e o papel do Isolation Forest (que, na avaliação, não acrescentou detecção ao LOF).
- **As revisões automáticas não substituíram o julgamento.** Dos pontos levantados pelo Claude Code, parte foi corrigida, parte foi documentada como limitação e parte foi mantida de propósito, com justificativa (por exemplo, não alterar a fórmula de uma anomalia de avaliação só para melhorar o resultado do modelo).

## Decisões da equipe

A IA sugeriu opções e explicou conceitos; a equipe escolheu, validou contra os dados e assumiu cada decisão. Entre as decisões que partiram do integrante ou foram tomadas contra a sugestão inicial da IA:

- **Remover o horário de início das features do modelo.** A IA propôs uma anomalia de "recarga de madrugada"; o integrante apontou que o próprio modelo de rateio incentiva a recarga de madrugada, e o horário saiu do modelo.
- **Criar as anomalias de avaliação a partir de sessões reais**, e não de sessões sintéticas, para que a avaliação reflita o comportamento real do carregador.
- **Buscar o histórico completo na SEMS+**, o que ampliou a base de 18 para 225 sessões reais e permitiu treinar o modelo com dados reais.
- **Manter a regra de atribuição de energia ativa no laboratório**, mesmo disparando em sessões do lab, por sinalizar um problema real de instrumentação.
- **Manter o Isolation Forest e documentar** que, na avaliação atual, o LOF sozinho detectou todas as anomalias.

Todas as decisões técnicas e suas justificativas estão registradas em [`DECISOES.md`](DECISOES.md).
