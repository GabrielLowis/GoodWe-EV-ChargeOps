# EV ChargeOps - Gestão Inteligente de Recarga Compartilhada em Condomínios
**Enterprise Challenge 2026 · Parceria GoodWe × FIAP · Sprint 01 — Pesquisa e Documentação**
---
## Equipe
| Integrante | RM |
| --- | --- |
| Eduardo Lopes da Silveira Mota | 563418 |
| Gabriel Luís de Lima Ramos | 568984 |
| Mayara Luisa Vicente Rosa | 571955 |
| Victor de Camargo Gomes | 568912 |
| Matheus Silveira | 570447 |

---
## Sumário
1. [O problema e o contexto do desafio](#1-o-problema-e-o-contexto-do-desafio)
2. [Frente 1 - Contexto e Problema](#2-frente-1--contexto-e-problema)
3. [Frente 2 - Base Regulatória e Técnica](#3-frente-2--base-regulatória-e-técnica)
4. [Frente 3 - Arquitetura e IA](#4-frente-3--arquitetura-e-ia)
5. [Diagrama de arquitetura](#5-diagrama-de-arquitetura)
6. [Modelo de rateio](#6-modelo-de-rateio)
7. [O papel da IA na solução](#7-o-papel-da-ia-na-solução)
8. [Plano para a Sprint 02](#8-plano-para-a-sprint-02)
9. [Fontes consultadas](#9-fontes-consultadas)
---
## 1. O problema e o contexto do desafio
Com o crescimento acelerado da frota de veículos elétricos no Brasil, os condomínios residenciais enfrentam um novo desafio: como disponibilizar infraestrutura de recarga de forma compartilhada, organizada e financeiramente justa entre os moradores. A simples instalação de carregadores não resolve o controle de acesso, a medição individualizada de consumo nem o rateio dos custos de energia.
No cenário típico de condomínio, o ponto de recarga é alimentado pela rede das áreas comuns, o mesmo relógio que mede elevadores, iluminação e bombas. Essa energia entra no rateio condominial e é dividida entre todos na taxa mensal, fazendo com que **quem não tem carro elétrico acabe subsidiando a recarga de quem tem**. 
Daí nasce o problema central: medir e atribuir a cada usuário exatamente o que ele consumiu, transformando uma despesa coletiva e opaca em uma cobrança individual e rastreável.
O **EV ChargeOps** (Electric Vehicle Charge Operations) é a resposta a esse problema: uma plataforma de gestão de recarga de veículos elétricos voltada a condomínios, desenvolvida em parceria com a GoodWe. A solução apoia-se no hardware **GoodWe HCA G2** e comunica-se com ele pelo ecossistema nativo da GoodWe **Modbus TCP** na rede local e **API SEMS** na nuvem, considera o enquadramento regulatório da ANEEL e oferece um modelo de faturação e rateio que distribui os custos de forma transparente.
> **A pergunta que organiza o projeto:** como transformar sessões de recarga em uma infraestrutura compartilhada em dados estruturados, rateio justo e inteligência acionável, com IA como motor lógico?
**Decisões transversais do MVP** (definidas na Frente 3 e que orientam toda a solução):
- **Cenário de referência:** carregador rotativo em condomínio, atendendo múltiplos moradores em um mesmo ponto físico, não o cenário simplificado de uma vaga por unidade. É o cenário que o desafio propõe e que a infraestrutura real do laboratório FIAP (HCA G2 instalado na Unidade Aclimação) reproduz.
- **Comunicação:** ecossistema GoodWe (Modbus TCP localmente e API SEMS na nuvem), **sem OCPP** o HCA G2 não o implementa. O OCPP fica registrado como vetor de evolução futura, não como compromisso arquitetural do MVP.
- **Identificação do morador:** por **reserva prévia no aplicativo**, e não por cadastro individual de cartão RFID no firmware, contornando o limite de dez cartões por equipamento e preservando a escalabilidade para condomínios com dezenas de unidades.
---
## 2. Frente 1 - Contexto e Problema
A Frente 1 percorre as camadas que se sobrepõem na prática condominial, infraestrutura elétrica, individualização do consumo, segurança, disponibilidade e moldura jurídica e consolida o problema em uma proposta de solução.
### 2.1 Itens obrigatórios
**Infraestrutura de recarga compartilhada e desafios de gestão.** A diferença essencial em relação à recarga doméstica está em por onde a energia é medida: em casa, o carregador fica atrás do medidor do próprio morador; no condomínio, costuma ser alimentado pela rede comum e diluído na taxa. Os desafios operacionais agrupam-se em cinco eixos: (a) **capacidade elétrica e risco de sobrecarga**, já que o pico de recarga coincide com o pico residencial; (b) **individualização do consumo e cobrança justa**; (c) **segurança e conformidade normativa** (ABNT NBR 5410, NBR 17019, NBR IEC 61851-1, NR-10 e instruções do Corpo de Bombeiros, com emissão de ART); (d) **disponibilidade, filas e agendamento**; e (e) **lacunas regulatórias e responsabilidade do síndico**.
**Como funciona uma sessão de recarga.** O foco do condomínio é a recarga em **corrente alternada (CA)**, em que o carregador (wallbox) entrega CA e o conversor interno do veículo faz a conversão para CC. É a recarga lenta/semirrápida viável dentro da capacidade elétrica de um prédio comum, ao contrário da recarga ultrarrápida (DC), cara e raramente cabível em ambiente residencial.
**Modelos de negócio.** Mapeamos os formatos praticados no Brasil e no mundo, gratuito, por kWh, por tempo, assinatura mensal e rateio condominial, analisando vantagens e limitações de cada um para o contexto condominial.
### 2.2 Opções de aprofundamento escolhidas
Foram desenvolvidas **as três opções** (A, B e C), formando um triângulo de evidências:
- **Opção A -  Análise de mercado.** Mapeamento de cinco soluções em operação: **Zaptec Pro** (Noruega), **Wallbox Pulsar Plus** (Espanha), **ChargePoint** (EUA), **NeoCharge** (Brasil) e **EMEL/LEVE** (Portugal, recarga pública municipal). Conclusão: balanceamento de carga, medição individual e app já são padrão de mercado; o espaço de diferenciação está no **rateio condominial automatizado, na tarifa por horário (inspirada na Tarifa Branca) e na aderência à regulação brasileira**, justamente onde o EV ChargeOps se posiciona.
- **Opção B - Pesquisa de campo.** Questionário aplicado a moradores de um condomínio real, com **78 respostas**. Achados-chave: 88% têm intenção de adquirir um EV e 100% afirmam não haver ponto de recarga hoje (cenário *greenfield*); 96% rejeitam ratear a recarga alheia e 99% valorizam medição individual; 91% preferem pagar por kWh consumido; 96% aprovariam a instalação em assembleia se a cobrança fosse individual; entre quem já tem EV, 100% aceitam tarifa por horário **desde que o agendamento seja automático**. A pesquisa transforma o agendamento inteligente de diferencial técnico em **requisito de adoção**.
- **Opção C - Análise de dados públicos.** Dimensionamento do mercado a partir de ABVE, Tupi Mobilidade, NeoCharge/Senatran e McKinsey: a frota de eletrificados cresce em ritmo próximo da duplicação anual (48.591 emplacamentos só no 1º bimestre de 2026, +90% sobre 2025), enquanto a rede de recarga avança ~42% ao ano. A projeção da McKinsey aponta ~580 mil carregadores até 2030, dos quais ~490 mil residenciais e de frota, confirmando que o esforço de eletrificação se concentra na **recarga privada e compartilhada**, o território do EV ChargeOps.
---
## 3. Frente 2 - Base Regulatória e Técnica
A Frente 2 mapeia o ambiente normativo e o equipamento, convertendo cada fragilidade jurídica em uma decisão de projeto.
### 3.1 Itens obrigatórios
**Seis camadas normativas.** A recarga compartilhada no Brasil é regulada por seis planos sobrepostos: **setorial/energia** (REN ANEEL 1.000/2021, 1.059/2023 e Lei 14.300/2022), **técnico-normativa** (ABNT/NBR e NR-10), **industrial/fomento** (Programa Mover - Lei 14.902/2024), **tributária** (ICMS × ISS, com transição para IBS/CBS), **condominial/civil** (Código Civil e Lei SP 18.403/2026) e **proteção de dados** (LGPD). O ponto-chave da camada setorial é que o EV ChargeOps **não revende energia**: presta um serviço de recarga, atribui a cada morador o consumo que foi dele e cobra por esse serviço ,  atividade comercial livre, sem necessidade de concessão.
**Carregador GoodWe HCA G2 - interfaces.** O equipamento (modelos GW7K, GW11K e GW22K-HCA-20; 7 a 22 kW AC) troca dados por cinco interfaces, cada uma com um papel na solução:
| Interface | Função no equipamento | Papel no EV ChargeOps |
| --- | --- | --- |
| **RS-485** | Comunicação com o inversor (A1/B1) e o medidor MID (A2/B2) | Medição de energia por ponto (base do rateio) e controle dinâmico de carga |
| **LAN** | Conexão cabeada com o roteador e a nuvem SEMS | Telemetria estável das sessões até o back-end |
| **Wi-Fi** | Conexão sem fio (2,4 GHz) com a nuvem | Alternativa de telemetria (decisão de instalação) |
| **Bluetooth (BLE)** | Configuração local pelo app SolarGo | Comissionamento e manutenção (fora do fluxo de cobrança) |
| **RFID** | Identificação do usuário (13,56 MHz; até 10 cartões) | Atribuição da sessão ao usuário - restrição de escala tratada na arquitetura |

---

**API GoodWe (SEMS Portal / SEMS+).** A inspeção direta do ambiente *LAB FIAP Eco Smart Home* documentou o que a plataforma expõe sobre o carregador: estado operacional, potência instantânea, duração e energia por sessão (kWh), **separação por origem solar × rede por sessão** (campos Green / Grid / Charged), Card ID, porta de recarga e curva de potência. O achado decisivo: a obrigação regulatória de não tratar energia solar compensada como consumo da rede **já existe como dado nativo** na plataforma.
### 3.2 Opções de aprofundamento escolhidas
Foram desenvolvidas **as três opções**:
- **Opção A - Mapeamento regulatório completo.** Análise das seis camadas, incluindo a correção tributária sobre a transição para IBS/CBS (LC 214/2025, art. 28, e Decreto 12.955/2026, art. 15) e a exclusão da energia compensada como parâmetro dependente da modalidade de geração, não como dedução automática.
- **Opção B - Exploração da API GoodWe.** Documentação dos dados expostos pela SEMS+ por sessão e no nível da planta (energia por origem, séries de potência, tarifas, eventos/alarmes, agregados e dados meteorológicos), com a decisão de arquitetura de tolerar lacunas de telemetria via bufferização local e reconciliação posterior.
- **Opção C - APIs complementares.** Mapeamento do contraponto internacional (AFIR na UE, NEVI nos EUA, ISO 15118 e OCPP) e de fontes externas (previsão meteorológica via INMET) que alimentam a inteligência da solução.
**Síntese da Frente 2 - requisitos de produto:** imposto parametrizável por município/estado e período; campo de energia compensada na fatura; compromisso com o Modo 3 e o balanceamento dinâmico de carga; medição individual por sessão; *privacy by design* com contrato controlador/operador; e fatura transparente e auditável.
---
## 4. Frente 3 - Arquitetura e IA
A Frente 3 traduz o diagnóstico das Frentes 1 e 2 em arquitetura concreta.
### 4.1 As quatro camadas da plataforma
- **Camada física**  o carregador GoodWe HCA G2, o inversor/bateria/medidor MID e um **gateway local** (Raspberry Pi ou ESP32) que lê os dados via Modbus TCP, armazena cada sessão de forma persistente e sincroniza com a nuvem quando a internet permite. O gateway é a garantia de que nenhuma sessão se perde por intermitência da SEMS.
- **Camada de conectividade** -  duas vias paralelas: a **via local** (gateway ↔ carregador via Modbus TCP) e a **via nuvem** (carregador → SEMS → back-end). Em operação normal, o back-end consome preferencialmente a SEMS (que já separa solar × rede); quando a SEMS falha, o gateway local prevalece como fonte da verdade.
- **Camada de aplicação** - o cérebro da solução, em **Python + FastAPI** com **PostgreSQL**. Três módulos: ingestão e reconciliação, regras de negócio (modelo de rateio) e inteligência artificial.
- **Camada de apresentação** - duas interfaces sobre os mesmos endpoints REST: o **app do morador** (reservas, alertas, histórico, memória de cálculo e fatura) e o **painel do gestor** (sessões em tempo real, gestão de reservas, configuração de tarifas e overhead, fila de anomalias e relatório de arrecadação).
### 4.2 Fluxo de dados (da sessão à fatura)
O dado percorre sete etapas: **(1)** reserva no app → **(2)** início da sessão (cartão compartilhado + captura de timestamp e Card ID) → **(3)** telemetria contínua (potência, energia, separação solar/rede) → **(4)** encerramento e classificação (concluída, encerrada pelo usuário ou interrompida por falha) → **(5)** atribuição ao morador pela reserva + **verificação de anomalia (IA)** → **(6)** cálculo da fatura com memória célula a célula → **(7)** **recomendação da próxima janela (IA)**.
### 4.3 Opções de aprofundamento escolhidas
- **Opção A - Benchmarking de modelos de rateio.** Comparação entre o **rateio por consumo real (kWh)** e a **cobrança por tempo/sessão com tarifa de ociosidade**, justificando o **modelo híbrido** adotado (detalhado na seção 6).
- **Opção B - Definição do papel da IA.** Duas abordagens estruturais, previsão de janela ótima e detecção de anomalias (detalhadas na seção 7 e no documento de apoio `Papel_da_IA.docx`).
---
## 5. Diagrama de arquitetura

![arquitetura](https://github.com/VictorCamargo344/GoodWe-Sprint1/blob/main/Arquitetura_da_solucao.png)


## 6. Modelo de rateio
O modelo foi desenhado para satisfazer três princípios simultaneamente: **justiça** (cada morador paga apenas o que usou), **transparência** (memória de cálculo auditável célula a célula) e **parametrização** (faixas tarifárias, impostos e overheads definidos pela assembleia, não fixados no código).
### 6.1 Modelo escolhido: híbrido
A base é a **cobrança por consumo real de energia (kWh)** com fechamento mensal individual (justiça financeira do Modelo 1), acrescida de **regras de ociosidade/overstay** para evitar a ocupação indevida da vaga após o fim da recarga (eficiência operacional do Modelo 2). Essa combinação é a mais adequada a condomínios com muitos veículos elétricos e poucos pontos de recarga.
### 6.2 Composição da fatura individual
A fatura mensal de cada morador é a soma de todas as suas sessões válidas, com três parcelas por sessão:
| Variável | Critério de cálculo |
| --- | --- |
| **Energia verde** | kWh do campo *Green Charging* (SEMS) × preço Green da faixa horária da sessão |
| **Energia da rede** | kWh do campo *Grid Charging* (SEMS) × preço Grid da faixa horária da sessão |
| **Tempo de ociosidade** | Minutos após tolerância de 15 min do fim do fluxo de energia × taxa por minuto (assembleia) |

-- 

Sobre o subtotal incidem dois acréscimos: o **imposto** correspondente (ICMS, ISS ou IBS, conforme município e período da reforma tributária), destacado na fatura; e um **overhead operacional opcional**, percentual sobre o subtotal definido pela assembleia, que o condomínio pode zerar ou aplicar.
As **faixas horárias** (ponta, intermediário e fora de ponta) e seus preços espelham a lógica da Tarifa Branca da ANEEL e são definidas pela assembleia.
### 6.3 Reembolso ao condomínio
O condomínio paga à distribuidora a conta integral do mês. O valor arrecadado nas faturas individuais retorna ao caixa, **reembolsando exatamente o que foi gasto com a energia dos carros**. Resultado: quem não usa o carregador tem fatura zero (sem assinatura mínima), e a diluição na taxa condominial desaparece, o argumento que destrava a aprovação em assembleia deixa de ser promessa e passa a ser arquitetura.

### 6.4 Casos excepcionais
| Caso | Tratamento |
| --- | --- |
| **Sessão interrompida** | Paga-se apenas a energia entregue até a interrupção. Se a causa for falha do sistema (código de erro ou queda de comunicação), **não há cobrança**. A taxa de ociosidade não se aplica. |
| **Morador que não carregou no mês** | **Fatura zero**, sem mensalidade mínima nem taxa de disponibilidade. O sistema não distingue quem não tem EV de quem viajou: cobra apenas onde houve uso. |
| **Dois veículos da mesma unidade** | Cada morador é uma entidade individual, com cadastro, histórico e fatura próprios. Geram-se **duas faturas separadas**, atribuídas pelas reservas de cada um (consolidação em um pagador é preferência de pagamento, não de rateio). |
| **No-show de reserva** | Cartão não encostado em 20 min → reserva cancelada automaticamente e ponto liberado. Três no-shows em 30 dias → bloqueio temporário do direito de reservar (consequência comportamental, não financeira). |

---
### 6.5 Identificação e limite de cartões

O **cartão físico RFID** é um recurso compartilhado do condomínio (até 10 por carregador, custodiados pelo síndico). A **identidade do morador** vive no aplicativo, vinculada à reserva. O cruzamento entre reserva ativa e início de sessão (timestamp + Card ID) atribui a sessão à pessoa correta, escalando para qualquer número de moradores. Como rede de segurança, qualquer sessão sem reserva correspondente é atribuída ao dono cadastrado do cartão, evitando sessões órfãs.

---
## 7. O papel da IA na solução
A IA é adotada como **camada funcional estrutural, não decorativa**: cada técnica precisa atacar uma dor concreta que, sem ela, ficaria mal resolvida. Sob esse critério, **duas abordagens** se justificam, ambas operando sobre os dados que a SEMS e o gateway já entregam, sem instrumentação adicional. O detalhamento completo está no documento de apoio.

### 7.1 Abordagem 1 - Previsão para recomendação de janela ótima
**Problema:** o incentivo da tarifação horária é passivo, o morador não consegue antecipar a curva solar, o estado da bateria ou o impacto financeiro de carregar agora versus de madrugada, e tende a carregar no pico, anulando o ganho.
**Técnica:** regressão sobre séries temporais (regressão linear com features sazonais e gradient boosting / XGBoost) para prever geração solar e consumo do prédio nas próximas 24–48 h, alimentando uma função-objetivo que minimiza o custo previsto sob a restrição de capacidade elétrica.
**Dados:** histórico de sessões, geração fotovoltaica, SOC da bateria, tarifas por faixa e previsão meteorológica (INMET).
**Impacto:** converte o incentivo abstrato em economia visível ("carregar às 2h30 custa R$ X contra R$ Y agora") e achata a curva de demanda no pico para o condomínio.
### 7.2 Abordagem 2 - Detecção de anomalias de medição
**Problema:** medições internamente coerentes para o equipamento, mas contextualmente impossíveis (ex.: 50 kWh em um carregador de 7 kW em 90 min), passam pelos testes internos do HCA G2 e entrariam silenciosamente na fatura.
**Técnica:** modelos não supervisionados de detecção de outliers (**Isolation Forest** e **Local Outlier Factor**, via PyOD e scikit-learn), que aprendem o normal a partir do histórico da planta sem exigir rótulos de fraude prévios.
**Dados:** kWh, duração, potência média/máxima, razão kWh/duração, faixa horária, Card ID e curva de potência.
**Impacto:** sessão anômala é bloqueada antes de entrar na fatura e fica suspensa para revisão humana, protegendo a integridade da cobrança e construindo a **trilha auditável exigida pela LGPD (art. 20)**.

### 7.3 Por que essas duas, e não outras

Ambas (a) operam sobre dados já disponíveis, (b) são centrais ao produto, sem a previsão, a tarifação horária perde efetividade; sem a detecção, a memória de cálculo deixa de ser confiável e (c) são explicáveis, compatíveis com a LGPD. Clustering de perfis e chatbot por NLP foram considerados e descartados por ganho marginal ou risco de cair no critério de "decorativo".

---
## 8. Plano para a Sprint 02

A Sprint 02 transforma o que foi pesquisado e decidido nas Frentes 1, 2 e 3 em código consumindo dados reais do HCA G2 pela **API SEMS+**, com prazo de entrega em **20/09/2026**. O critério de fechamento é direto: uma sessão de recarga real precisa ser ingerida pela SEMS+ com separação solar × rede, atribuída ao morador correto pela reserva ativa, faturada conforme a Seção 6 com memória de cálculo expandível campo a campo, e atravessar os dois modelos de IA da Seção 7 antes de chegar ao morador no app e ao síndico no painel.

### 8.1 Escopo do MVP
Está dentro da sprint todo o fluxo de ponta a ponta descrito na Seção 4.2, com os dois modelos de IA da Seção 7 servidos como endpoints e as duas interfaces (morador e síndico) consumindo o mesmo back-end. Está fora da sprint, e fica explicitamente registrado como evolução futura, o suporte ao protocolo OCPP, a integração com gateway de pagamento (PIX automático e cartão de crédito), a separação por *tenancy* para múltiplos condomínios, a certificação metrológica para fins fiscais e a interface conversacional por NLP. A contenção é deliberada: cada uma dessas frentes vale uma sprint inteira por si só, e empacotá-las junto com o núcleo do produto comprometeria a qualidade do entregável principal.

A única fonte de dado real confirmada é a **API SEMS+**, já inspecionada pela equipe (Frente 2). Em consequência, o gateway local Modbus permanece no escopo arquitetural e é desenvolvido e demonstrado contra simulador, mas a validação Modbus TCP contra o equipamento físico fica registrada como atividade pós-sprint, condicionada à disponibilidade do laboratório da FIAP. O fluxo demonstrado na entrega final consome a SEMS+ como fonte primária; o gateway entra na demo como peça de resiliência exercitada com dados sintéticos.

### 8.2 Módulos a desenvolver
Os módulos são descritos na ordem da pilha (físico → conectividade → aplicação → apresentação), espelhando a Seção 4.

**Gateway local.** Roda em um Raspberry Pi 4 conectado à mesma sub-rede do HCA G2, lendo os registradores Modbus TCP do carregador a cada segundo. Mantém um *buffer* em SQLite local que serializa cada sessão completa (cabeçalho, série de potência, energia por origem, eventos) e tenta entregá-la ao back-end via REST. Em caso de falha de internet ou de indisponibilidade da SEMS, o *buffer* cresce localmente sem perda, e a entrega é retomada na primeira janela de conexão. O gateway é a garantia de que nenhuma sessão se perde e é também a fonte da verdade quando a SEMS está fora do ar.

**Back-end de ingestão e reconciliação.** Em Python 3.12 com FastAPI, recebe os dados de duas origens, o cliente da API SEMS (consultas periódicas) e o *endpoint* REST do gateway (entrega *push*), e os funde em um único registro de sessão. A regra de reconciliação é "SEMS quando disponível, gateway como *fallback*". Eventuais discrepâncias entre as duas fontes ficam registradas em uma tabela de auditoria para revisão posterior.

**Motor de rateio.** Aplica a fórmula da Seção 6 sobre as sessões persistidas e gera a fatura mensal individual. Cada parcela (energia verde, energia da rede, ociosidade, imposto e *overhead*) é calculada de forma isolada e a memória de cálculo correspondente é serializada como JSONB no Postgres, permitindo ao morador abrir a fatura linha por linha e ver exatamente quais sessões compõem o valor. Os quatro casos excepcionais da Seção 6.4 são tratados como caminhos explícitos no *engine*, não como exceções soltas no código.

**Reserva e atribuição de sessão.** É o módulo que converte cartão RFID compartilhado em identidade individual. O morador reserva uma janela no app; quando o cartão é apresentado ao HCA G2 dentro dessa janela, a sessão é atribuída automaticamente à reserva ativa. Para o caso de sessão sem reserva correspondente, a sessão é atribuída ao dono cadastrado do cartão como rede de segurança contra sessões órfãs. O agendamento é parametrizado pela capacidade simultânea do condomínio, com fila e cancelamento por no-show conforme a Seção 6.4.

**Inteligência artificial.** Os dois modelos da Seção 7 são empacotados como endpoints do back-end. O detector de anomalias (Isolation Forest e LOF, via PyOD) recebe a sessão recém-encerrada e retorna um *score*; sessões acima do limiar ficam suspensas na fila do gestor antes de entrarem na fatura. O preditor de janela ótima (regressão linear) consome o histórico de sessões, a curva de geração fotovoltaica do laboratório, e devolve para o app do morador uma recomendação de horário com o custo previsto associado.

**Interfaces.** O **app do morador**, em React + Vite + TypeScript entregue como PWA, cobre reserva, consulta de fatura mês a mês, abertura da memória de cálculo de cada sessão, recomendação de janela ótima e histórico de consumo. O **painel do síndico**, no mesmo *stack*, cobre visão em tempo real das sessões em andamento, configuração das faixas tarifárias e do *overhead*, fila de sessões suspeitas (saída do detector de anomalia) para aprovar ou rejeitar e relatório mensal de arrecadação para fechamento contábil com o condomínio.

### 8.3 Sequência de entrega
A sequência respeita as dependências de dados de cada módulo. Nenhum módulo entra antes de seus pré-requisitos estarem persistidos, o que evita retrabalho e mantém o *pipeline* testável de ponta a ponta a cada *commit*.

| Fase | Semanas | Entregas |
| --- | --- | --- |
| **1. Fundação** | 1–2 | Esquema PostgreSQL completo (usuário, unidade, reserva, sessão, fatura, tarifa, evento), *scaffolding* FastAPI com autenticação, repositório com CI no GitHub Actions e o **simulador Modbus do HCA G2**. O simulador é o que destrava todo o trabalho posterior, já que o carregador físico do laboratório está disponível apenas em janelas presenciais curtas. |
| **2. Ingestão e reconciliação** | 3–4 | Cliente da API SEMS, leitor Modbus no gateway, *endpoint* de recepção no back-end e tabela de auditoria das discrepâncias entre as duas fontes. |
| **3. Motor de rateio** | 5–7 | memória de cálculo serializada em JSONB, parametrização das faixas tarifárias e dos impostos e tratamento dos quatro casos excepcionais da Seção 6.4. |
| **4. Reserva e atribuição** | 8–9 | Fluxo de reserva no app, regra de atribuição automática da sessão à reserva ativa, fila e cancelamento por no-show. |
| **5. Inteligência artificial** | 10–11 | *Pipeline* de *features*, treino e *back-test* do detector de anomalia (Isolation Forest e LOF) e do preditor de janela ótima (regressão linear sazonal + XGBoost), com integração nos endpoints `/anomalias` e `/recomendacao-janela`. O treino inicial usa o dataset *Electric Vehicle Charging Sessions* do Kaggle; o ajuste fino acontece com os dados reais coletados no FIAP. |
| **6. Interfaces e integração final** | 12–13 | App do morador, painel do síndico e integração de ponta a ponta com a **API SEMS+** alimentada pelo HCA G2 do laboratório, com o gateway local exercitado contra simulador no mesmo cenário. Inclui a gravação do vídeo pitch de 3 minutos exigido pela prova presencial. |

### 8.4 Stack tecnológica

| Camada | Tecnologia | Decisão |
| --- | --- | --- |
| **Gateway local** | Raspberry Pi 4, `pymodbus`, SQLite | Hardware de baixo custo com Modbus TCP nativo e persistência local que sobrevive a quedas da nuvem. |
| **Back-end** | Python 3.12, FastAPI, SQLAlchemy, Alembic | Tipagem forte com Pydantic, validação automática nos contratos REST e ecossistema científico que permite à IA viver no mesmo *runtime* do back-end. |
| **Banco de dados** | PostgreSQL 16 | Transações ACID para a fatura, JSONB para a memória de cálculo e suporte nativo a séries temporais para a curva de potência das sessões. |
| **Inteligência artificial** | scikit-learn, PyOD, XGBoost, pandas | Cobre as duas frentes da Seção 7 com modelos explicáveis, compatíveis com a exigência de transparência algorítmica do art. 20 da LGPD. |
| **Front-end** | React, Vite, TypeScript, PWA | Mesma base de componentes serve ao app do morador e ao painel do síndico, sobre os mesmos endpoints REST; PWA evita o custo de manter app nativo nesta sprint. |
| **Infraestrutura de desenvolvimento** | Docker Compose, pytest, GitHub Actions | Ambiente reprodutível para back-end + banco + simulador em qualquer máquina da equipe, com *pipeline* de testes e *linters* a cada *commit*. |

### 8.5 Riscos e mitigações

| Risco | Mitigação |
| --- | --- |
| **Acesso restrito ao HCA G2 físico** | A SEMS+ é a fonte primária da demo, e a equipe já validou o acesso à API. O gateway Modbus é desenvolvido contra simulador na Fase 1 e demonstrado no mesmo ambiente; a validação Modbus TCP contra o equipamento físico fica condicionada à abertura de janela presencial no laboratório, sem bloquear a entrega da sprint. |
| **Indisponibilidade pontual da API SEMS+** | O *buffer* SQLite do gateway, ainda que validado em simulador, demonstra arquiteturalmente como a operação real absorveria quedas da SEMS+ sem perda de sessão. Para a demo, sessões já coletadas durante a Sprint 01 ficam em cache local para repetição offline. |
| **Histórico insuficiente para treinar a IA** | Treino inicial sobre o dataset público *Electric Vehicle Charging Sessions* do Kaggle, com ajuste fino sobre os dados reais à medida que são coletados; Isolation Forest e LOF não exigem rótulos prévios, o que torna a abordagem viável mesmo com histórico pequeno. |
| **Estouro de escopo no front-end** | App do morador e painel do síndico compartilham a base de componentes e os mesmos endpoints, reduzindo duplicação. Eventuais cortes vão primeiro para o painel do síndico, que aceita ser mais cru no MVP, antes de tocar na experiência do morador. |

### 8.6 Critérios de aceitação
A Sprint 02 será considerada concluída quando os seis critérios abaixo forem satisfeitos:

1. A fatura mensal exibe as cinco parcelas (energia verde, energia da rede, ociosidade, imposto e *overhead*) com memória de cálculo expandível campo a campo no app do morador.
2. Uma sessão anômala injetada artificialmente (com kWh fisicamente impossível para a potência do equipamento) é bloqueada pelo detector de anomalia antes de entrar na fatura e aparece na fila de revisão do síndico.
3. O app do morador permite reservar uma janela, consultar a fatura do mês corrente e visualizar a recomendação de janela ótima para as próximas 24 horas com o custo previsto.
4. O painel do síndico exibe sessões em tempo real, permite configurar faixas tarifárias e *overhead* e gera o relatório mensal de arrecadação para fechamento com o condomínio.
5. O vídeo pitch de 3 minutos exigido pela prova presencial está gravado e o repositório está documentado com README atualizado, diagrama de arquitetura e instruções de execução.

---
## 9. Fontes consultadas
Todas as fontes abaixo foram efetivamente consultadas pela equipe e correspondem às referências dos três documentos de pesquisa (Frentes 1, 2 e 3). Datas de acesso entre junho de 2026, conforme registrado em cada frente.

### 9.1 Frente 1 - Contexto e Problema

**Frota, mercado e infraestrutura**
- ABVE. *Recarga pública rápida cresce 167% em 12 meses e já atinge 31% dos 21 mil eletropostos da rede*. Associação Brasileira do Veículo Elétrico, 2026. https://abve.org.br/recarga-publica-rapida-cresce-167-em-12-meses-e-ja-atinge-31-dos-21-mil-eletropostos-da-rede/
- AUTOINDÚSTRIA. *Já são 21 mil pontos de recarga de carro elétrico no Brasil*, 4 mar. 2026. https://www.autoindustria.com.br/2026/03/04/ja-sao-21-mil-postos-de-recarga-de-carro-eletrico-no-brasil/
- CANALVE. *Frota de eletrificados no Brasil ultrapassa 700 mil unidades (ABVE)*, 2026. https://canalve.com.br/frota-eletrificados-brasil-ultrapassa-700-mil-unidades/
- CANALVE. *Frota de eletrificados no Brasil cresce 28% no primeiro semestre (NeoCharge/Senatran)*, 2025. https://canalve.com.br/frota-eletrificados-brasil-cresce-28-primeiro-semestre/
- ELÉTRICOS BRASIL. *Mapa de eletropostos e tipos de recarga*. https://www.eletricos.app/mapa-eletropostos
- GAZETA DO POVO. *Rede de recarga avança no Brasil para acompanhar a alta dos elétricos*, 2026. https://www.gazetadopovo.com.br/energia/carros-eletricos-rede-recarga-avanca-brasil-acompanhar-alta/
- GAZETA DO POVO. *Como o Brasil está expandindo a rede de recarga para carros elétricos*, 2026. https://www.gazetadopovo.com.br/energia/como-o-brasil-esta-expandindo-a-rede-de-recarga-para-carros-eletricos/
- McKINSEY & COMPANY. *Recarregar para crescer: o futuro da infraestrutura de recarga de veículos elétricos no Brasil*, 2025. https://www.mckinsey.com/br/our-insights/all-insights/recarregar-para-crescer
- TERRA. *Brasil rompe a barreira dos 20 mil eletropostos com salto histórico na recarga rápida (ABVE)*, 2026.

**Tarifa Branca e gestão de carga**
- AGÊNCIA INFRA. *Área técnica da ANEEL propõe Tarifa Branca automática a partir de 2026*, 6 nov. 2025. https://agenciainfra.com/blog/area-tecnica-da-aneel-propoe-tarifa-branca-automatica-a-partir-de-2026/
- ANEEL. *Tarifa Branca: introdução*. https://www.gov.br/aneel/pt-br/assuntos/tarifas/tarifa-branca/introducao
- CANAL SOLAR. *Tarifa branca: conceitos e especificações na medição de energia elétrica*, 20 maio 2025. https://canalsolar.com.br/tarifa-branca-conceitos-e-especificacoes-na-medicao-de-energia-eletrica/
- EDP BRASIL. *Tarifa branca*. https://www.edp.com.br/tarifa-branca/
- ENEL. *Tarifa Branca - Enel Distribuição São Paulo*. https://www.enel.com.br/pt-saopaulo/tarifa-branca.html
- ELETRICPAY. *Balanceamento de carga para carregamento de veículos em condomínios*. https://eletricpay.com/balanceamento-de-carga-para-carregamento-de-veiculos-em-condominios/

**Condomínio, jurisprudência e OCPP**
- CHARGEGURU. *Carregamento de veículos elétricos em condomínios*, 2026. https://chargeguru.com/pt/carregamento-em-condominios/
- CONSULTOR JURÍDICO (CONJUR). *Instalação de carregador de carro elétrico em prédio exige aprovação de assembleia*, 18 jan. 2024. https://www.conjur.com.br/2024-jan-18/instalacao-de-carregador-de-carro-eletrico-em-predio-exige-aprovacao-de-assembleia/
- MIGALHAS. *Moradora não pode instalar carregador veicular sem aval de condomínio*, 19 nov. 2025. https://www.migalhas.com.br/quentes/444793/moradora-nao-pode-instalar-carregador-veicular-sem-aval-de-condominio
- NEOCHARGE. *OCPP - Protocolo de Ponto de Carga Aberto*. https://www.neocharge.com.br/tudo-sobre/carregador-carro-eletrico/protocolo-ocpp
- NICAIRA RODRIGUES ADVOCACIA. *Carregador de carro elétrico em condomínio: guia completo para síndicos*, 11 ago. 2025. https://nicairarodriguesadvocacia.com.br/carregador-de-carro-eletrico-em-condominio-guia-completo-para-sindicos/
- O ELECTRICISTA. *As soluções de carregamento OCPP da TEV*, 4 mar. 2026. https://www.oelectricista.pt/as-solucoes-de-carregamento-ocpp-da-tev/
- POWER2GO. *FAQ - Instalação de carregadores para veículos elétricos em condomínios*, 27 jun. 2025. https://www.power2go.com.br/post/faq-instalação-de-carregadores-para-veículos-elétricos-em-condomínios
- SINDICONET. *Carregador de carro elétrico em condomínio*, 23 jan. 2024. https://www.sindiconet.com.br/informese/carregador-de-carro-eletrico-em-condominio-colunistas-fernando-augusto-zito
- UCONDO. *Carregadores de carros elétricos nos condomínios*. https://www.ucondo.com.br/blog/carregadores-de-carros-eletricos-nos-condominios
- VOLTBRAS. *Benefícios do Protocolo OCPP na gestão de eletropostos*, 1 jul. 2025. https://voltbras.com/uncategorized-pt/beneficios-do-protocolo-ocpp-na-gestao-de-eletropostos/

**Normas e legislação citadas (Frente 1)**
- ABNT. NBR 5410 (instalações de baixa tensão); NBR 17019 (infraestrutura de recarga de EV); NBR IEC 61851-1 (carga condutiva).
- BRASIL. Lei nº 10.406/2002 (Código Civil - arts. 1.335, 1.341, 1.342); Ministério do Trabalho, NR-10.
- SÃO PAULO (Estado). Lei nº 18.403/2026; SÃO PAULO (Município). Lei nº 17.336/2020.
- CORPO DE BOMBEIROS PMESP. Instrução Técnica IT-41 e Portaria 003/970/2026 (SAVE).
- Pesquisa de campo (dados primários): questionário aplicado a moradores de um condomínio residencial (78 respostas), jun. 2026. Elaboração própria.

### 9.2 Frente 2 - Base Regulatória e Técnica

- ANEEL. Resolução Normativa nº 1.000, de 7 dez. 2021. https://www2.aneel.gov.br/cedoc/ren20211000.html
- ANEEL. Resolução Normativa nº 1.059, de 7 fev. 2023. https://www2.aneel.gov.br/cedoc/ren20231059.html
- ANEEL. Resolução Normativa nº 819, de 19 jun. 2018 (revogada). https://www2.aneel.gov.br/cedoc/ren2018819.html
- ANEEL. *Veículos Elétricos*. https://www.gov.br/aneel/pt-br/assuntos/veiculos-eletricos
- BRASIL. Lei nº 14.300/2022 (Marco Legal da GD) - Fio B. https://canalsolar.com.br/tarifacao-fio-b-lei-14-300/
- BRASIL. Lei nº 14.902/2024 (Programa Mover); Decreto nº 12.435/2025. https://www.planalto.gov.br/ccivil_03/_Ato2023-2026/2024/Lei/L14902.htm
- BRASIL. Decreto nº 12.955, de 29 abr. 2026 (regulamento da CBS), art. 15. https://www.planalto.gov.br/ccivil_03/_ato2023-2026/2026/decreto/d12955.htm
- BRASIL. Lei Complementar nº 214/2025, art. 28; Lei Complementar nº 116/2003 (item 14.01); Súmula 391 do STJ; Emenda Constitucional nº 132/2023.
- CONJUR. *A ascensão da mobilidade elétrica e o dilema tributário no carregamento de veículos: ICMS ou ISS?*, 25 jul. 2025. https://www.conjur.com.br/2025-jul-25/a-ascensao-da-mobilidade-eletrica-e-o-dilema-tributario-no-carregamento-de-veiculos-icms-ou-iss/
- SEFAZ-SP. Resposta a Consulta RC 30579/2024 (ICMS sobre recarga). https://legislacao.fazenda.sp.gov.br/Paginas/RC30579_2024.aspx - e RC 31007/2024.
- Condomínio: Lei SP 18.403/2026 (SindicoNet). https://www.sindiconet.com.br/informese/lei-recarga-carros-eletricos-condominios-sp-2026-noticias-juridico
- CÂMARA DOS DEPUTADOS. PL 158/2025 - instalação de ponto de recarga em condomínio. https://www.camara.leg.br/noticias/1134716-projeto-regulamenta-instalacao-de-ponto-individual-de-recarga-de-carro-eletrico-em-condominio/
- ABNT. NBR 17019:2022; NBR IEC 61851 (partes 1, 21, 22, 23, 24); NBR IEC 62196. https://canalsolar.com.br/abnt-publica-norma-para-instalacao-de-carregadores-de-veiculos-eletricos/
- CELESC. Instrução Normativa I-321.0043 - Estações de recarga. https://www.celesc.com.br/arquivos/normas-tecnicas/padrao-entrada/I-321-0043-Estacoes-de-recarga-de-veiculos-eletricos.pdf
- GOODWE. HCA G2 Series AC Charger (página oficial e datasheet). https://en.goodwe.com/hca-g2
- CANAL SOLAR. *GoodWe HCA G2 - análise técnica*. https://canalsolar.com.br/en/goodwe-hca-g2-electric-vehicle-charging/
- UNIÃO EUROPEIA. Regulation (EU) 2023/1804 (AFIR). https://transport.ec.europa.eu/transport-themes/clean-transport/alternative-fuels-sustainable-mobility-europe/alternative-fuels-infrastructure_en
- IEA. *Regulation (EU) 2023/1804 - Alternative Fuels Infrastructure Regulation*. https://www.iea.org/policies/27375-regulation-eu-20231804-alternative-fuels-infrastructure-regulation
- OPEN CHARGE ALLIANCE. Open Charge Point Protocol (OCPP) - versões 1.6 / 2.0.1; ISO 15118.
- WAY2. *LGPD no setor elétrico*. https://way2.com.br/blog/lgpd-no-setor-eletrico/ - e BRASIL, Lei nº 13.709/2018 (LGPD).
- GOODWE. SEMS Portal / SEMS+ (endpoints a confirmar na Sprint 02). https://semsplus.goodwe.com
- GOODWE TECHNOLOGIES. Manual do usuário - Carregador CA Série HCA (7–22 kW) G2, V1.5, 11 nov. 2025 (modelos GW7K/GW11K/GW22K-HCA-20).
- Inspeção direta do ambiente *LAB FIAP Eco Smart Home* (SEMS+), realizada em 17/06/2026.

### 9.3 Frente 3 - Arquitetura e IA

- CHARGEPOINT. *Improving transparency with per-kWh billing for EV charging in Canada*, 7 nov. 2023. https://www.chargepoint.com/blog/improving-transparency-kwh-billing-ev-charging-canada
- CÂMARA DOS DEPUTADOS. *Projeto multa motorista que permanecer em vaga depois de recarregar carro elétrico*. https://www.camara.leg.br/noticias/1259657-projeto-multa-motorista-que-permanecer-em-vaga-depois-de-recargar-carro-eletrico/
- NEOCHARGE. *Carregador para carro elétrico em prédios e condomínios: instalação*. https://www.neocharge.com.br/tudo-sobre/carregador-carro-eletrico-predio-condominio-instalacao
- SCHNEIDER ELECTRIC. *Electrical Distribution Fundamentals Design Guide - Electric Vehicle Charging* (0100DB2301). https://productinfo.se.com/0100db2301_elecdistfunddesignguide/
- ZAPTEC. *Zaptec Pro - Load and phase balancing for shared charging* (documentação do fabricante; referência cruzada na análise de mercado da Frente 1).

### 9.4 Soluções de mercado adicionais (benchmark da Frente 1)

- WALLBOX. *Pulsar Plus / myWallbox Business* (datasheet e documentação do fabricante).
- EMEL / LEVE. Operadora de Pontos de Carregamento de Lisboa, integrada à rede pública MOBI.E.
- ESTADOS UNIDOS. Programa NEVI - National Electric Vehicle Infrastructure (padrões mínimos de financiamento federal).
