# Frente 5 — escopo e planejamento do frontend

**Projeto:** EV ChargeOps — GoodWe × FIAP  
**Data:** 08/10/2026  
**Situação:** referência do escopo amplo. Este documento não autoriza iniciar a implementação das telas.

**Atualização de 08/10/2026:** o trabalho foi reorganizado em [quatro entregas para o prazo da faculdade](ENTREGAS-FRENTE5.md), considerando quatro sessões de duas horas e entrega em 13/10. O plano atualizado prevalece: desenvolvimento somente de frontend, sem trabalho adicional de segurança/escala e com cadastros complexos como extras. Qualquer alteração no backend ou banco depende de aprovação específica do usuário; a proposta de endpoint da seção 9 não está autorizada.

## 1. O que estamos construindo

O EV ChargeOps organiza o uso de um carregador de carro elétrico compartilhado em um condomínio. O morador reserva um horário, consulta suas recargas e entende a cobrança. O síndico acompanha a agenda, verifica problemas nas medições, configura os preços e gera as faturas.

A Frente 5 é a parte visual desse sistema: as páginas, os menus, os formulários e as mensagens que as pessoas usam no navegador, pelo celular ou pelo computador.

Será uma única aplicação com duas áreas, conforme o perfil da pessoa que entrar:

| Área | Quem utiliza | Principal objetivo |
|---|---|---|
| Morador | Pessoa que utiliza o carregador | Reservar e acompanhar suas próprias recargas e cobranças |
| Síndico | Gestor do condomínio | Administrar o uso do carregador e o faturamento |

**Resultado esperado:** conseguir demonstrar o fluxo completo pelas telas, usando a API e o banco de verdade, com sessões simuladas claramente identificadas. A conexão física com o equipamento GoodWe continua sendo uma pendência de outra frente.

## 2. O que já existe e o que falta

| Já preparado | Ainda será desenvolvido neste escopo |
|---|---|
| Backend com login, reservas, sessões, anomalias, tarifas e faturas | Telas e navegação para utilizar essas funções |
| PostgreSQL e estrutura das tabelas | Apresentação dos dados do banco pela API |
| Motor de rateio, que calcula a cobrança | Explicação visual das parcelas e da memória de cálculo |
| Detector de anomalias | Fila de análise e formulário de decisão do síndico |
| Estimativa de melhor horário | Formulário de consulta e comparação dos custos previstos |
| Base React/TypeScript e conexão com a API | Componentes, layout, formulários e estados de carregamento/erro |
| Estrutura inicial para instalar o site como aplicativo | Acabamento e verificação da instalação e da mensagem offline |
| Scripts e simulador | Roteiro de demonstração das telas e evidências da entrega |

O frontend conversa com o backend; o backend consulta o banco e executa os cálculos. Não colocaremos as regras financeiras nem as credenciais do banco dentro das páginas.

## 3. Termos que aparecerão nas telas

| Termo | Significado simples |
|---|---|
| Reserva | Horário agendado para utilizar um conector do carregador |
| Sessão | Registro de uma recarga: início, fim, energia entregue e resultado da validação |
| Green | Parte da energia registrada como proveniente da fonte solar |
| Grid | Parte da energia registrada como proveniente da rede elétrica |
| kWh | Unidade que indica a quantidade de energia consumida |
| kW | Unidade de potência; influencia quanto tempo a recarga pode levar |
| Ociosidade | Tempo de ocupação depois do fim da entrega de energia; pode gerar cobrança após a tolerância configurada |
| Overhead | Acréscimo operacional configurado pelo condomínio |
| Anomalia | Medição suspeita, inconsistente ou sem morador identificado, que exige análise |
| Fatura | Cobrança mensal individual do morador |
| Memória de cálculo | Explicação de como cada valor da fatura foi obtido |

Reserva, sessão e fatura são registros diferentes. Reservar uma vaga não começa uma recarga; consultar uma fatura não significa que ela foi paga.

## 4. Acesso, cadastro e navegação

| Função proposta | O que faremos |
|---|---|
| Login | E-mail e senha, mostrar/ocultar senha, mensagens de erro e indicação de envio |
| Identificação do perfil | Após autenticar, abrir a área do morador ou a do síndico automaticamente |
| Cadastro de morador | Nome, e-mail, senha e unidade já cadastrada; a pessoa não escolhe virar síndico |
| Sair | Limpar a sessão no navegador e voltar ao login |
| Proteção das páginas | Quem não estiver autenticado volta ao login; morador não acessa a área administrativa |
| Sessão expirada | Explicar que é necessário entrar novamente; não perder silenciosamente o resultado de uma ação |
| Navegação | Menus próprios por perfil, indicação da página atual e caminhos claros para voltar |

**Proposta para esta entrega:** manter o token apenas em memória, como a base atual. Recarregar a página ou fechar o aplicativo exige novo login. O recurso “lembrar de mim”, renovação automática e manutenção do login após fechar o navegador ficam fora desta primeira versão.

O cadastro de morador é uma inclusão proposta neste relatório; o plano original exige login. Se você preferir demonstrar apenas com contas previamente criadas, essa tela pode ser retirada na validação.

Não haverá criação de síndico pelo cadastro público. A conta administrativa inicial continua sendo preparada pelo ambiente.

## 5. Área do morador

### 5.1. Início

Mostrar o nome e a unidade do morador, sua próxima reserva, as recargas recentes e a última fatura disponível, sempre identificando o período dos dados. Oferecer atalhos para reservar, consultar recomendações, ver histórico e abrir a fatura.

Se a pessoa nunca reservou ou carregou, apresentar um estado vazio com a próxima ação possível. Se ainda não existe fatura gerada, mostrar “nenhuma fatura disponível”, sem inventar uma fatura de valor zero. Uma fatura zero só aparece quando esse registro realmente existe no backend.

**Aceite:** cada cartão corresponde aos dados da pessoa autenticada e leva à tela correta. Valores de cobrança vêm da API.

### 5.2. Reservar e acompanhar reservas

O morador poderá escolher carregador, conector, data e horários de início e fim. A agenda apresentará os intervalos ocupados e permitirá consultar uma janela livre. Antes de salvar, mostrar um resumo do agendamento; depois, confirmar a reserva retornada pela API.

Também haverá uma lista das próprias reservas, com filtros de período/status e cancelamento das reservas que ainda podem ser canceladas.

Regras que a interface precisa explicar:

- A reserva começa no futuro e tem duração máxima de 12 horas.
- Uma janela ocupada não pode ser reservada no mesmo conector.
- Outra pessoa pode reservar entre a consulta da agenda e o clique em confirmar; nesse caso, atualizar a disponibilidade e explicar o conflito.
- O morador não vê nomes nem dados das pessoas que ocupam outros horários.
- Se houver bloqueio temporário por faltas, explicar o impedimento e a data informada pelo backend.
- Reservar não envia comando para iniciar o carregador.

**Aceite:** criar e cancelar uma reserva pelas telas altera os registros reais, e o conflito de horário é tratado sem duplicar agendamentos.

### 5.3. Recomendação de horário

Receber o carregador, a quantidade de energia desejada em kWh e a potência prevista em kW. Mostrar horário e duração sugeridos, custo estimado, comparação com carregar agora e economia estimada.

Oferecer “Usar este horário”, levando os dados para o formulário de reserva. O morador ainda confirma a reserva, e a API consulta novamente se a janela está disponível. A sugestão não bloqueia a vaga.

A tela usará a recomendação que existe hoje: uma estimativa para as próximas 24 horas, com tarifas cadastradas e geração solar hipotética. Exibirá as premissas e não prometerá um valor final garantido. Não apresentaremos essa estimativa como previsão de IA treinada com clima e histórico.

**Aceite:** a comparação usa os valores da API; ausência de tarifa ou de janela disponível tem uma explicação compreensível.

### 5.4. Histórico e detalhe das sessões

Listar as recargas da pessoa, com data, duração, carregador, energia e situação da validação. Permitir filtros de período, carregador e status, e abrir o detalhe de uma sessão.

No detalhe, apresentar início, fim, fim da entrega de energia quando conhecido, Green/Grid, potências disponíveis e identificação da origem simulada. Informação ausente será apresentada como indisponível.

A interface distinguirá:

| Informação | Exemplos de apresentação |
|---|---|
| Como a recarga terminou | Concluída, interrompida pelo usuário ou falha do sistema |
| Se pode seguir para cobrança | Aguardando validação, aprovada, suspensa para revisão ou rejeitada |

Uma sessão aprovada pode ainda não ter entrado em uma fatura. A tela não presumirá que “aprovada” significa “cobrada” ou “paga”.

**Aceite:** morador consulta somente suas sessões; os estados são traduzidos em linguagem clara, sem mostrar códigos técnicos como explicação principal.

### 5.5. Faturas e memória de cálculo

Mostrar a lista de faturas por mês, com total e situação: aberta ou fechada. Ao abrir uma fatura, mostrar as sessões incluídas e separar os valores de energia Green, energia Grid, ociosidade, impostos e overhead.

O detalhe de cada sessão explicará as faixas de horário, energia distribuída entre elas, preços utilizados, regra de ociosidade e demais parcelas. Mostrar observações importantes, como sessão excluída da cobrança ou recarga de mês anterior liberada após revisão.

A explicação deve permitir responder: “quanto estou sendo cobrado?” e “por que esse valor?”. Os valores e critérios serão os retornados pelo motor; o navegador não recalculará a conta para substituir o backend.

Regras já existentes a apresentar quando aplicáveis:

- Falha do sistema não gera cobrança.
- Parada voluntária não gera taxa de ociosidade.
- Sem evidência do fim da energia, não inventar minutos de ociosidade.
- Ausência de consumo faturável pode resultar em fatura zero.
- Fatura fechada preserva os valores registrados.

**Aceite:** o total e as parcelas exibidos coincidem com a API, e os motivos das exclusões/isenções são visíveis. Não haverá botão de pagamento.

### 5.6. Perfil

Mostrar nome, e-mail, unidade e perfil de acesso. A versão proposta é de consulta: editar perfil, trocar senha e excluir conta não entram nesta entrega, porque esses fluxos não possuem suporte na API atual.

## 6. Área do síndico

### 6.1. Visão geral

Apresentar reservas próximas, sessões recentes, quantidade de anomalias pendentes e resumo financeiro do período escolhido. Os valores financeiros virão do relatório do backend. Contagens e filtros de listas podem ser organizados na interface.

Mostrar a data da atualização e um botão de atualizar. Não haverá indicadores inventados de carregador online, recarga em andamento ou energia instantânea.

**Aceite:** cada indicador tem período/origem definidos e permite abrir a lista relacionada.

### 6.2. Carregadores

Listar código, modelo, potência nominal, quantidade de conectores, localização e situação do cadastro. Incluir formulário para cadastrar um equipamento com código, número de série, modelo, potência, conectores e localização.

Separar “equipamento cadastrado/ativo” de “equipamento conectado agora”. O estado de conexão física aparece como indisponível enquanto não houver telemetria. O detector atual foi treinado no HCA01 de 7 kW; cadastrar outro equipamento não garante aprovação automática de suas medições.

**Aceite:** cadastro utiliza a API e trata dados inválidos/duplicados. Edição, exclusão, ativação/desativação e controle remoto ficam fora desta versão.

### 6.3. Agenda e reservas

Mostrar a agenda do condomínio e a lista de reservas, com identificação do morador/unidade, carregador, conector, período e situação. Incluir filtros e cancelamento permitido pelo backend.

Oferecer uma ação manual para processar faltas, com explicação e confirmação antes de enviar. Depois, atualizar as reservas e indicar o resultado. O botão não será apresentado como processamento automático.

O backend atual considera falta após 20 minutos do início sem sessão atribuída; três faltas nos últimos 30 dias geram bloqueio demonstrativo de sete dias. Esses critérios serão exibidos como a política atual. Alterá-los pelo painel não faz parte desta proposta.

### 6.4. Sessões do condomínio

Listar e detalhar as sessões de todos os moradores, com filtros de período, pessoa, carregador, origem e situação. Identificar sessões sem morador e levar à análise correspondente quando houver anomalia.

Usar a mesma apresentação de recarga/memória quando possível, ampliando somente as informações permitidas ao gestor. Não permitir editar manualmente a energia medida ou os valores de uma sessão.

### 6.5. Anomalias e revisão

Separar pendentes, aprovadas e rejeitadas. Ao abrir uma ocorrência, apresentar a sessão relacionada, os motivos em português, o morador quando identificado e os dados necessários para revisar.

O síndico poderá aprovar ou rejeitar e registrar uma observação. Para aprovar uma sessão sem reserva/morador, deverá selecionar um morador ativo. Quando a sessão já está ligada a uma reserva, o formulário preserva o morador daquela reserva.

Antes de enviar, mostrar um resumo da decisão. Depois, atualizar a ocorrência e apresentar responsável, data e observação da revisão. Uma ocorrência já revisada não terá um segundo formulário de decisão.

O score da IA, se exibido, será explicado como indicador relativo de suspeita, não como probabilidade. Aprovar uma ocorrência não cria automaticamente uma fatura nem dispensa as verificações do motor de cobrança.

**Aceite:** revisão é persistida com auditoria; atribuição de órfã funciona; erros e revisões concorrentes são explicados sem sobrescrever uma decisão existente.

### 6.6. Tarifas

Apresentar as versões cadastradas, a vigência e os preços por faixa. O formulário de nova versão incluirá:

- Nome, início da vigência e referência da decisão do condomínio, quando houver.
- Preço do kWh Green e Grid nas faixas fora de ponta, intermediária e ponta.
- Horários das janelas intermediárias/de ponta.
- Tolerância de ociosidade e valor por minuto excedente.
- Percentual de overhead.
- Regra para finais de semana e feriados fora de ponta.

Mostrar um resumo antes de salvar, porque a nova versão encerra a vigência da versão aberta. Validar campos, faixas duplicadas e janelas inválidas/sobrepostas; o backend continua responsável pela validação definitiva.

**Aceite:** criar uma nova versão preserva o histórico. A tela não oferece alteração destrutiva de preços usados em faturas.

### 6.7. Configurações e unidades

Permitir consultar/cadastrar unidades do condomínio, com bloco e número. Permitir consultar regras de imposto e criar uma nova versão, com tipo, jurisdição, alíquota, vigência, tratamento da energia Green e referência quando aplicável.

O painel explicará que a criação de uma versão encerra a regra aberta do mesmo tipo e jurisdição. Os parâmetros de demonstração serão identificados como tais; não definiremos um enquadramento fiscal real neste trabalho.

Fuso horário, jurisdição padrão e política de faltas serão consultáveis, sem formulário de edição nesta versão. Overhead e ociosidade serão configurados em Tarifas, evitando duas telas que alterem o mesmo parâmetro.

Não haverá gestão completa de usuários, promoção de morador a síndico ou edição/exclusão das unidades existentes.

### 6.8. Financeiro

Permitir selecionar mês/ano, consultar faturas e gerar/recalcular faturas abertas para um morador ou para o conjunto de moradores. Mostrar resultados e explicar as sessões não incluídas. Uma operação recusada por existir fatura fechada deverá informar o motivo.

Permitir abrir a memória de cálculo e fechar uma fatura individual, com confirmação explícita: depois do fechamento, aquela fatura não poderá ser recalculada pela aplicação.

O relatório mensal mostrará os valores de energia, ociosidade, impostos, overhead, total faturado, moradores/faturas do período e balanço da energia faturada ou excluída. Incluir lançamentos posteriores quando retornados pela API.

**Aceite:** relatório e faturas usam os totais da API. O texto da tela será “faturamento”, sem indicar que esses valores já foram recebidos. Não haverá controle de pagamento, dívida paga ou emissão fiscal.

## 7. Experiência visual e uso no celular

A aplicação será em português, com valores em reais, datas legíveis e horários do condomínio. O morador terá navegação simples adequada ao celular; o síndico terá um painel que também funcione em telas menores.

Antes de desenvolver os fluxos, prepararemos um mapa de navegação e esboços das telas principais para validar hierarquia e distribuição das informações. A proposta visual inicial é sóbria, com boa leitura, cores consistentes e componentes reaproveitados. Paleta final, marca e exemplos de layout serão validados antes de aplicar o acabamento a todas as telas.

O trabalho inclui botões, campos, mensagens, listas/tabelas, etiquetas de situação, filtros, confirmações e detalhes expansíveis. Conteúdo precisa continuar utilizável por teclado, com foco visível, rótulos nos campos e informação de status além da cor.

Todas as consultas/escritas terão tratamento para:

| Situação | Comportamento esperado |
|---|---|
| Carregando | Indicação de espera e prevenção de envio duplicado |
| Sem dados | Explicação e próxima ação possível |
| Campo inválido | Mensagem próxima ao campo e preservação dos dados digitados |
| Sem conexão/serviço indisponível | Mensagem clara e opção de tentar novamente |
| Acesso expirado ou proibido | Solicitar login ou explicar a restrição |
| Conflito de dados | Atualizar o registro/agenda e explicar por que a ação foi recusada |
| Sucesso | Confirmação baseada na resposta da API e atualização da lista/detalhe |

Filtros e divisão em páginas poderão ser feitos sobre as listas disponíveis nesta entrega acadêmica. Paginação no servidor para grandes volumes não faz parte do escopo inicial.

## 8. Instalação como aplicativo e modo offline

Preparar a aplicação para instalação como PWA: site que pode ser adicionado à tela inicial de dispositivos compatíveis. Incluir ícones adequados, nome, aparência básica de aplicativo e verificação em navegador compatível no build de produção.

Sem conexão, mostrar uma página clara de indisponibilidade e orientar a reconectar. Reservar, revisar, configurar preços e consultar dados atualizados continuarão dependendo do backend. Não guardaremos faturas, dados pessoais ou tokens no cache offline.

A verificação local pode comprovar o comportamento em navegador compatível. Teste em celular físico depende de um endereço acessível ao aparelho e do ambiente necessário para instalar a PWA; essa condição será registrada, sem declarar validação em dispositivo que não foi testado.

## 9. Ajustes técnicos previstos

O trabalho principal acontecerá em `frontend/`: organização das páginas, rotas, componentes, formulários, autenticação, consulta da API, apresentação de erros e testes.

O cliente tipado já existente será mantido. Alterações de contrato precisam atualizar a documentação da API e os tipos gerados, para não existir uma versão diferente dos dados em cada lado.

**Ajuste pequeno de backend proposto para acompanhar as telas:** disponibilizar uma consulta autenticada de configurações públicas, limitada ao fuso do condomínio, jurisdição padrão e regras de faltas já aplicadas. Esse retorno não incluirá segredos. Evita repetir no frontend valores que hoje ficam apenas no código/configuração do servidor.

Se os testes de uma tela revelarem uma incompatibilidade na API atual, corrigiremos somente o contrato/erro necessário àquele fluxo e registraremos a mudança. Funcionalidades novas de backend que ampliem o produto voltam para validação de escopo.

Não estão previstos refazer o banco, substituir o motor de rateio, retreinar a IA com novos critérios ou conectar equipamentos físicos. Gráficos de curva de potência ficam fora da entrega inicial: os detalhes atualmente expostos pela API não incluem essa série de medições.

## 10. Demonstração e dados

Usaremos as contas de demonstração e um conjunto controlado de cenários no banco de desenvolvimento. O simulador seguirá separado do uso normal do morador; não criaremos um botão de “iniciar recarga” que apenas fabrique dados sem explicar isso.

O roteiro incluirá reserva normal, conflito de horário, cancelamento, sessão normal, sessão suspeita, sessão sem morador, revisão, falha sem cobrança, fatura zero e fatura com memória de cálculo.

Os registros de demonstração serão identificados como simulados. O roteiro utilizará os estados efetivamente suportados pelo backend e não exigirá abrir uma fatura fechada ou apagar dados do projeto para funcionar.

## 11. O que fica fora desta entrega

| Fora do escopo | Limite da entrega proposta |
|---|---|
| Integração física GoodWe, SEMS e Modbus | Demonstrar por sessões simuladas no contrato real da API |
| Acompanhamento ao vivo, bateria e controle remoto | Histórico e dados disponíveis; sem iniciar/parar o equipamento pelas telas |
| Nova IA de recomendação, clima ou previsão solar real | Tela para o estimador determinístico atual, com suas premissas |
| PIX, cartão, comprovantes e controle de recebimentos | Exibir e administrar faturas, sem executar pagamentos |
| Nota fiscal e motor tributário completo | Mostrar/configurar parâmetros acadêmicos já suportados |
| Aplicativo nativo Android/iOS | Aplicação web responsiva com instalação PWA |
| Recuperação de senha, troca de senha, login social | Login/cadastro básico compatível com a API |
| Login persistente após fechar/recarregar | Sessão em memória; novo login quando necessário |
| Notificações push, e-mail, SMS e WhatsApp | Mensagens dentro da aplicação durante o uso |
| Vários condomínios e gestão completa de pessoas | Um condomínio e os cadastros necessários aos fluxos descritos |
| Exportação PDF/CSV e relatórios personalizados | Relatório e memória de cálculo consultáveis nas telas |
| Gráficos avançados, chat ou gamificação | Apresentação clara dos dados necessários |
| Trabalho operacional totalmente offline | Página offline; ações dependem de conexão |
| Agendamento automático e edição da política de faltas | Processamento manual pelo síndico, conforme backend atual |
| Hospedagem pública, publicação no GitHub e implantação externa | Entrega local reproduzível e instruções de execução |

Docker e CI já estão preparados, mas sua execução não foi comprovada no computador atual. Não trataremos essa evidência como concluída; executar essas verificações em ambiente compatível é uma pendência compartilhada, separada das telas.

## 12. Ordem de execução após validar o escopo

| Etapa | Entrega verificável |
|---|---|
| 1. Navegação e esboços | Mapa das áreas, telas principais e direção visual para validar |
| 2. Estrutura e acesso | Componentes comuns, rotas, login, cadastro proposto, perfil e proteção por papel |
| 3. Reservas e home | Agenda, disponibilidade, criação/cancelamento e início do morador |
| 4. Recargas e cobrança do morador | Histórico, detalhe, faturas e memória de cálculo |
| 5. Operação do síndico | Visão geral, agenda administrativa, sessões, revisão e atribuição de órfãs |
| 6. Administração financeira | Tarifas, impostos, unidades, geração/fechamento e relatório mensal |
| 7. Recomendação | Comparação de custos e uso do horário sugerido no formulário de reserva |
| 8. Acabamento e entrega | Responsividade, acessibilidade, PWA, testes finais, roteiro e documentação |

A integração e os testes acontecerão a cada fluxo. Não deixaremos toda a conexão com backend/banco para a última etapa. Prazo de calendário será definido depois da validação do escopo e da disponibilidade para revisão.

## 13. Como vamos verificar se está funcionando

| Verificação | Evidência esperada |
|---|---|
| Componentes/formulários | Campos, erros, estados vazios e prevenção de envio duplicado testados |
| Login e permissões | Morador e síndico chegam às áreas certas; acesso indevido é recusado também pela API |
| Reservas | Criar e cancelar reservas e tratar conflito de horário pela interface, com registro persistido |
| Sessões e revisão | Dados da API visíveis; aprovação/rejeição e atribuição persistidas com responsável |
| Financeiro | Valores apresentados iguais aos da API; gerar/recalcular/fechar preserva regras do backend |
| Resiliência | Erro de rede, sessão expirada e dados indisponíveis possuem mensagens e saída compreensível |
| Navegador | Percursos completos executados com backend e PostgreSQL reais, usando dados simulados identificados |
| Layout/acessibilidade | Conferência em largura de celular e desktop, teclado, foco e legibilidade |
| PWA | Build de produção, comportamento offline e instalação nos ambientes efetivamente testados |
| Regressão | Build/testes do frontend e testes de backend pertinentes continuam passando |

Testes com respostas simuladas ajudam a verificar as telas, mas não substituem a demonstração com API e banco reais. Os testes já existentes da preparação não comprovam automaticamente as telas que ainda serão criadas.

## 14. Critérios para considerar a Frente 5 entregue

- [ ] Login e navegação por perfil funcionam.
- [ ] Morador reserva, cancela, consulta recargas e entende sua fatura.
- [ ] Recomendação apresenta estimativa e permite preencher uma reserva sem prometer disponibilidade garantida.
- [ ] Síndico consulta agenda/sessões, revisa anomalias e atribui sessões órfãs.
- [ ] Síndico cadastra os parâmetros incluídos, gera faturas abertas, fecha faturas e consulta o relatório.
- [ ] Valores financeiros são os do backend; não há indicadores de pagamento ou telemetria inventados.
- [ ] Estados de carregamento, vazio, erro e sucesso estão presentes nos fluxos.
- [ ] Uso em celular/desktop e acesso por teclado foram verificados.
- [ ] PWA e limites offline estão implementados e documentados com evidência do ambiente testado.
- [ ] Há roteiro reproduzível de demonstração, instruções e registro dos testes da nova interface.
- [ ] As entregas originais e os dados existentes foram preservados.

## 15. Decisões para você validar

Este é o pacote proposto. Na validação, você pode aprovar, retirar ou adiar qualquer item antes da implementação.

| Decisão | Proposta deste relatório |
|---|---|
| Extensão da entrega | Área completa do morador e painel mínimo funcional do síndico, com todos os fluxos descritos |
| Cadastro de morador | Incluir; pode ser retirado se a apresentação usar somente contas previamente criadas |
| Perfil | Consulta dos dados; edição e troca de senha ficam fora |
| Sessão de login | Manter em memória nesta versão; recarregar exige autenticar novamente |
| Recomendação | Usar o estimador disponível e explicar seus limites |
| Configurações | Preços/impostos editados por novas versões; política de faltas/fuso só consultáveis |
| Visual | Validar navegação e esboços antes do acabamento completo |
| Dados da apresentação | API/banco reais e recargas simuladas identificadas |
| Alteração de backend | Consulta autenticada das configurações não sigilosas e correções pontuais de integração |
| Publicação | Entrega local; hospedagem/GitHub dependem de solicitação posterior |

**Nada neste relatório significa que as telas já foram implementadas.** Esta etapa entrega o escopo para sua revisão; o desenvolvimento começa após você validar o que deve entrar.

## Referências do projeto

- [Plano recebido da Sprint 2](reference/sprint2-plano.pdf), páginas 8–9: objetivos da Frente 5.
- [Contratos atuais do frontend](FRONTEND.md).
- [Decisões e limitações da integração](INTEGRATION.md).
- [Registro da validação da base](VALIDATION.md).
- [OpenAPI gerado da aplicação](openapi.json).

O escopo foi conferido com os schemas e rotas ativos em backend/api. As escolhas de UX e os limites listados acima são propostas desta etapa, não funcionalidades já entregues nem novas exigências atribuídas ao documento original.
