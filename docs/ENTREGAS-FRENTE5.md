# Frente 5 — quatro entregas para o prazo da faculdade

> Plano salvo em 08/10/2026, preservado como histórico de escopo/prioridades. Expressões de trabalho futuro e checklist abaixo são daquele planejamento. Estado funcional posterior: [RESOLUCAO-OVERVIEW](../frontend/RESOLUCAO-OVERVIEW.md). Entrega acadêmica: [ENTREGA-ACADEMICA](ENTREGA-ACADEMICA.md).

**Planejamento atualizado em:** 08/10/2026.  
**Prazo de apresentação/entrega:** 13/10/2026.  
**Disponibilidade considerada:** quatro sessões de aproximadamente duas horas, total de oito horas junto com o assistente. Uma terceira hora eventual é folga, não requisito do plano.  
**Nesta etapa:** organizar o trabalho. As telas ainda não estão implementadas.

Este documento adapta o [escopo anterior](PLANEJAMENTO-FRENTE5.md) ao prazo e às novas instruções. Em caso de diferença, **este plano prevalece**. O objetivo é uma aplicação acadêmica funcional, com visual simples, que permita apresentar os principais fluxos de morador e síndico.

Oito horas é um orçamento apertado para os dois perfis. As durações abaixo são estimativas para orientar prioridades, não uma garantia. Não tentaremos executar todo o relatório anterior nesse tempo. Se um fluxo consumir mais tempo, cortaremos primeiro os extras e simplificaremos sua apresentação.

## 1. Limites do trabalho

- Desenvolver somente o frontend, aproveitando a base React e o cliente da API existentes.
- Consumir as rotas já prontas. As ações das telas podem criar reservas, revisar sessões e gerar faturas **pela API existente**; isso faz parte do funcionamento normal, sem alterar código do backend ou estrutura do banco.
- Não criar rotas, migrations, tabelas, regras financeiras, modelos de IA ou infraestrutura.
- Se alguma função precisar de mudança no backend/banco, avisar o problema concreto e aguardar sua aprovação para essa mudança. Continuar os demais fluxos independentes enquanto isso.
- Não incluir trabalho adicional de cibersegurança, escala, auditorias de segurança ou preparação para produção. Aproveitar o login e os perfis que já existem, necessários para mostrar os dados e ações corretos.
- Usar as contas de demonstração existentes. Sem cadastro público como requisito.
- Usar os valores financeiros retornados pelo backend. O frontend apenas apresenta os dados.
- Manter sessões simuladas identificadas. A apresentação não inclui conexão física com o carregador.

**Retirado do plano anterior:** a proposta de criar um endpoint de configurações e a autorização genérica para corrigir o backend durante o desenvolvimento. Nenhuma alteração dessas está autorizada neste trabalho.

## 2. Visão das quatro entregas

Cada entrega é um pacote funcional, com várias telas/ações relacionadas. As tarefas internas não viram novas entregas.

| Entrega | O que estará utilizável ao terminar | Tempo previsto |
|---|---|---|
| 1. Acesso e reservas | Entrar, navegar como morador/síndico e criar/cancelar reservas | Cerca de 2 h |
| 2. Área do morador | Consultar recargas, entender a fatura e pedir sugestão de horário | Cerca de 2 h |
| 3. Operação do síndico | Acompanhar reservas/sessões e aprovar ou rejeitar anomalias | Cerca de 2 h |
| 4. Financeiro e apresentação | Gerar/fechar faturas, consultar parâmetros e testar o percurso completo | Cerca de 2 h |

## 3. Entrega 1 — acesso, navegação e reservas

**Resultado:** o projeto já pode ser usado para entrar e agendar uma recarga.

Inclui:

- Tela de login com e-mail, senha, erro de acesso e botão de sair.
- Abertura da área correspondente ao perfil retornado pela API.
- Layout simples compartilhado, menu e títulos das páginas. Sem etapa separada de prototipação ou aprovação de cada detalhe visual.
- Início do morador com nome, unidade e atalhos. Os resumos de sessões/fatura serão completados na entrega 2.
- Lista dos carregadores disponíveis no cadastro e escolha do conector.
- Formulário de reserva com data, início e fim.
- Consulta de disponibilidade como lista de horários ocupados. Sem construir um calendário gráfico complexo.
- Lista das próprias reservas e cancelamento quando permitido pela API.
- Mensagens básicas de carregamento, sucesso, campo inválido e conflito de horário.

**Como validar:** entrar com a conta de morador, criar uma reserva, verificar que ela aparece na lista, tentar uma janela ocupada e cancelar uma reserva. Entrar como síndico deve abrir a área administrativa, que será completada nas próximas entregas.

**API utilizada:** login, perfil atual, unidades para identificação, carregadores, disponibilidade e reservas. Nenhuma rota nova.

**Limite:** manter o comportamento de login da base atual; recarregar a página exige entrar novamente. Não construir cadastro, recuperação de senha ou persistência de sessão.

## 4. Entrega 2 — recargas, faturas e recomendação do morador

**Resultado:** o morador consegue acompanhar o uso e entender quanto foi faturado.

Inclui:

- Histórico das sessões e detalhe com horário, carregador, energia Green/Grid, origem e situação.
- Lista das faturas e detalhe com mês, total e situação aberta/fechada.
- Memória de cálculo em seções simples: parcelas retornadas, sessões incluídas e observações. Sem reproduzir as fórmulas no navegador nem exigir gráficos.
- Diferença visível entre recarga concluída e sessão aprovada para cobrança.
- Consulta do horário recomendado informando carregador, energia desejada e potência.
- Horário e custo estimados retornados pela API, com indicação de que usam geração solar hipotética.
- Ação para preencher a reserva com a sugestão; o morador ainda confirma o agendamento.
- Complemento da página inicial com próxima reserva, sessões recentes e última fatura disponível.
- Perfil consultável em um bloco simples com nome, e-mail e unidade, sem uma tela elaborada.

**Como validar:** abrir uma sessão e uma fatura existentes, conferir os valores com a resposta da API, consultar uma recomendação e levar o horário ao formulário de reserva. Se não houver registros, mostrar ausência de dados sem inventar recargas/faturas.

**API utilizada:** sessões, faturas, perfil e recomendação já existentes.

**Limite:** nenhuma edição de perfil, pagamento, exportação, gráfico de potência ou previsão solar nova.

## 5. Entrega 3 — operação do síndico

**Resultado:** o síndico acompanha o condomínio e resolve uma sessão que exige revisão.

Inclui:

- Visão geral simples com contagens de reservas, sessões e anomalias pendentes, usando as listas da API.
- Agenda administrativa em lista/tabela com moradores, horários e situação; cancelamento quando permitido.
- Lista de sessões de todos os moradores e detalhe reutilizado da entrega 2.
- Fila de anomalias com separação básica entre pendentes e revisadas.
- Detalhe dos motivos da ocorrência e dos dados da sessão.
- Aprovar ou rejeitar uma ocorrência e enviar uma observação.
- Selecionar um morador ativo ao aprovar uma sessão sem responsável identificado, conforme a API exige.
- Atualizar as listas após a decisão. A tela informa uma recusa da API quando a ocorrência já foi revisada.

**Como validar:** entrar como síndico, consultar as listas, revisar uma ocorrência disponível e conferir o resultado persistido. A atribuição de sessão sem morador também deve ser demonstrada se houver esse cenário no conjunto de dados disponível.

**API utilizada:** reservas, sessões, anomalias e usuários já existentes.

**Limite:** não editar medições, alterar regras da IA, construir filtros combinados complexos ou inventar status de equipamento online. A lista pode começar com os filtros essenciais de situação.

## 6. Entrega 4 — financeiro, consultas administrativas e fechamento

**Resultado:** o fluxo da apresentação fica completo e o projeto pode ser executado e demonstrado.

Inclui:

- Seleção de mês/ano e consulta das faturas pelo síndico.
- Geração/recalculo das faturas abertas com a rota pronta, inicialmente para o conjunto de moradores.
- Detalhe da fatura reutilizado da entrega 2.
- Fechamento individual com confirmação simples e explicação de que a fatura não pode ser recalculada depois.
- Resumo mensal do relatório de faturamento, sem tratá-lo como dinheiro recebido.
- Uma página administrativa de **consulta**, reunindo carregadores, unidades, tarifas e impostos já cadastrados. Sem formulários complexos de novas versões nesta entrega principal.
- Conferência do layout no computador e em uma largura de celular, corrigindo impedimentos de uso.
- Complemento básico do manifest/ícones da PWA e conferência do aviso offline existente no build de produção. Teste de instalação conforme o ambiente disponível, sem reservar uma etapa extensa para dispositivos diferentes.
- Build do frontend, testes já existentes e percurso manual das ações principais com a API e o banco do projeto.
- Instruções curtas de execução e roteiro da apresentação, registrando o que foi efetivamente testado.

**Divisão sugerida da sessão:** aproximadamente uma hora para concluir financeiro/consultas e uma hora para verificação e roteiro. Testes dos outros fluxos já acontecem nas entregas anteriores.

**Como validar:** gerar uma fatura aberta, consultar suas parcelas, conferir o resumo mensal, fechar uma fatura apropriada para demonstração e percorrer o sistema com as duas contas. Não fechar antecipadamente a fatura que ainda precisaremos recalcular no roteiro.

**API utilizada:** geração/listagem/detalhe/fechamento de faturas, relatório mensal e consultas dos cadastros existentes.

**Limite:** não instalar infraestrutura, publicar o site, modificar dados diretamente no banco ou prometer instalação em aparelho que não foi testado.

## 7. O que sai do pacote principal para caber no prazo

O relatório anterior continua como referência das possibilidades. Os itens abaixo **não são compromissos das quatro entregas**.

| Item do escopo anterior | Decisão para este prazo |
|---|---|
| Cadastro de morador | Usar as contas existentes; adicionar somente se sobrar tempo |
| Cadastro de carregadores e unidades | Consulta incluída; formulários ficam como extras |
| Criar versões de tarifas e impostos | Consulta incluída; configuração completa fica como extra |
| Botão para processar faltas/no-show | Extra; sem alterar política ou criar agendamento automático |
| Geração de fatura para um morador selecionado | Começar com geração do conjunto; seleção individual é extra |
| Muitos filtros, paginação e dashboard detalhado | Listas simples, filtros essenciais e resumo mensal |
| Mapa visual, wireframes e validações de design separadas | Definir um layout simples durante a entrega 1 e reutilizar |
| Acabamento fino, animações e revisão extensa de experiência | Apenas o necessário para ler e operar os fluxos |
| Suíte nova abrangente e automação de todos os percursos | Build, testes existentes e conferência prática dos fluxos; testes novos só para problemas concretos que precisarem deles |
| Testar todos os cenários extremos e vários celulares | Priorizar o roteiro acadêmico e registrar os limites verificados |
| Endpoint de configurações, correções de backend/banco | Fora; qualquer necessidade depende de aprovação específica |
| Segurança adicional, escala e produção | Fora; aproveitar a base atual sem ampliar esse trabalho |

Extras só entram depois que o pacote principal funcionar e a verificação final estiver preservada. Não serão trocados pelo tempo reservado para testar a apresentação.

Também continuam fora: integração física, pagamentos, nova IA, telemetria ao vivo, notificações, exportações, aplicativo nativo e funcionamento completo sem internet.

## 8. Agenda sugerida e regra para imprevistos

| Sessão | Sugestão de data | Meta |
|---|---|---|
| 1 | 08/10 | Acesso e reservas |
| 2 | 09/10 | Área do morador |
| 3 | 10/10 | Operação do síndico |
| 4 | 12/10 | Financeiro, verificação e apresentação |
| Entrega acadêmica | 13/10 | Apresentar/entregar o resultado |

As datas das sessões podem ser redistribuídas conforme sua disponibilidade, mantendo quatro sessões e a conclusão antes do dia 13. O dia 11 não conta como uma quinta sessão necessária. O orçamento continua sendo oito horas.

Se houver atraso, a ordem é: retirar extras, reduzir detalhes visuais/filtros e reutilizar mais telas. Se ainda faltar tempo para uma função principal, avisar qual é e combinar o corte; não declarar a Frente 5 completa enquanto essa pendência existir.

Se aparecer uma incompatibilidade da API, registrar **qual tela está impedida, qual retorno/rota está faltando e qual alteração seria necessária**. Não corrigir backend/banco automaticamente nem substituir a integração por dados inventados para esconder o problema.

## 9. Percurso da apresentação

1. Entrar como morador e mostrar sua área.
2. Consultar sugestão de horário, criar uma reserva e consultar/cancelar uma reserva.
3. Mostrar uma recarga simulada já registrada e sua situação.
4. Entrar como síndico e mostrar agenda, sessões e revisão de uma ocorrência disponível.
5. Gerar uma fatura aberta e consultar o relatório mensal.
6. Voltar ao morador, abrir a fatura e explicar as parcelas.
7. Mostrar o fechamento pelo síndico e a consulta dos parâmetros cadastrados.

O roteiro depende de existirem sessões e ocorrências adequadas no banco de desenvolvimento. Conferiremos essa disponibilidade no início, usando as consultas existentes. O simulador já preparado pode alimentar a demonstração sem alterar seu código; qualquer cenário que exija mudar backend/banco será apresentado para aprovação. Não criaremos uma tela falsa de recarga física.

## 10. Quando considerar o pacote concluído

- [ ] Login e menus dos dois perfis funcionam.
- [ ] Morador cria/cancela reservas e consulta recomendação, sessões e faturas.
- [ ] Fatura mostra valores e observações retornados pelo backend.
- [ ] Síndico consulta a operação e revisa anomalias.
- [ ] Síndico gera/consulta/fecha faturas e vê o resumo mensal.
- [ ] Cadastros e parâmetros existentes podem ser consultados.
- [ ] As telas indicam espera, ausência de dados e erros que impedem uma ação.
- [ ] Build e percurso principal foram conferidos; limitações da PWA/dados estão registradas.
- [ ] Instruções e roteiro permitem repetir a apresentação local.
- [ ] Nenhum backend, schema de banco ou infraestrutura foi alterado sem aprovação específica.

**Próximo passo:** desenvolver a entrega 1 quando você mandar começar. Esta organização não inicia a implementação.
