# Decisões técnicas — Frente 4 (IA e Ciência de Dados)

Registro das decisões tomadas durante o desenvolvimento do módulo de detecção de anomalias do CondoCharge, com o motivo de cada uma. Inclui os desvios em relação ao planejado na Sprint 1.

## 1. Arquitetura

- **Verificação em três camadas, em sequência.** Toda sessão passa por validação estrutural (Camada 1), regras físicas (Camada 2) e modelo de ML (Camada 3), parando na primeira que barrar. A ordem vai do mais barato e mais certo para o mais caro e mais incerto: formato errado e física impossível são certeza; o ML é uma suspeita estatística. Assim o síndico recebe o motivo mais preciso possível e o modelo não é consultado à toa.
- **Uma única função de entrada, `check_session`.** O backend chama só ela e recebe sempre o mesmo formato: `is_anomaly`, `score`, `layer`, `reasons`, `reasons_human` e `model_version`.
- **Módulo importado pelo backend, não serviço HTTP separado.** Menos infraestrutura para o protótipo. A interface pode virar um endpoint no futuro sem mudar o contrato.
- **Sessão suspeita não é cobrada automaticamente.** Ela vai para a fila de revisão do síndico com o motivo em português. Atende ao direito de revisão de decisões automatizadas (LGPD, art. 20) previsto na Sprint 1.

## 2. Dados

- **Fonte: SEMS+, sem acesso ao equipamento.** Nenhum integrante tem acesso físico ao HCA G2 do laboratório, então os dados vieram da plataforma SEMS+. O gateway local com Modbus TCP, previsto na Sprint 1, ficou fora do protótipo.
- **225 sessões reais extraídas (15/10/2025 a 02/10/2026).** A extração foi feita na interface da SEMS+ com apoio de uma extensão de IA para navegador, apenas em modo de leitura. Foram usadas só as sessões da fase de uso regular (mesmo cartão, recarga noturna quase diária); a fase anterior, de comissionamento e testes do instalador, foi descartada por representar outro regime de uso.
- **Correção do campo green em 35 sessões.** Nessas sessões o green veio cerca de 10 vezes maior que o total (ex.: total 5,2 kWh, green 52,0), padrão de vírgula decimal lida errado na extração. Quando o green passa do dobro do total, ele é dividido por 10.
- **10 sessões sem energia separadas.** Sessões com até 0,25 kWh (carro plugado sem carregar) não entram como sessões normais; são usadas como caso real na avaliação. O limite é o mesmo da regra `NO_ENERGY_DELIVERED`, definido num único lugar (`rules.py`): as sessões reais sem recarga vão até 0,24 kWh e as normais começam em 0,75 kWh.
- **Separação temporal entre treino e validação.** As 172 sessões mais antigas treinam o modelo e as 43 mais recentes (a partir de 23/07/2026) validam. Simula o uso real: treinar com o histórico e aplicar em sessões futuras.

## 3. Camada 1 — validação estrutural

- **Pydantic para validar o formato.** Campos obrigatórios, tipos, datas em ISO 8601 e status restrito a uma lista fechada (`Enum`). Erros viram os códigos `MISSING_FIELD` ou `INVALID_FIELD`.

## 4. Camada 2 — regras físicas

- **Nove regras determinísticas:** `INVALID_TIMESTAMP`, `NEGATIVE_KWH`, `DURATION_TOO_SHORT`, `UNKNOWN_CHARGER`, `POWER_EXCEEDS_NOMINAL`, `KWH_EXCEEDS_CAPACITY`, `ENERGY_SOURCE_ATTRIBUTION_MISMATCH`, `NO_ENERGY_DELIVERED` e `AVERAGE_EXCEEDS_MAX_POWER`.
- **Cadastro de carregadores por potência nominal.** As regras de potência e capacidade consultam um dicionário por carregador, o que deixa a solução pronta para condomínios com vários carregadores.
- **Tolerância de 5% nas regras de potência e capacidade.** Medidores reais oscilam um pouco acima do valor nominal, e as regras devem barrar só o que é claramente impossível. É uma margem de segurança, não um valor calibrado com dado real: no laboratório, a potência nunca passou de 3,5 kW, bem abaixo do limite de 7,35 kW.
- **Piso de 0,1 kWh na regra de atribuição.** Com dado real, duas sessões pequenas foram marcadas à toa porque a SEMS mostra o green com uma casa decimal (ex.: 0,7 de 0,75 kWh). A tolerância passou a ser o maior entre 5% do total e 0,1 kWh.
- **A regra de atribuição continua ativa mesmo disparando no laboratório.** No lab, a SEMS registra quase toda a energia como solar e às vezes zera as duas origens. A regra sinaliza esse problema de instrumentação antes do rateio, em vez de escondê-lo.
- **"Desconexão anormal" não é motivo de bloqueio.** Aparece em ~12% das sessões reais, inclusive em sessões que carregaram normalmente.
- **Regra própria para sessão sem recarga (`NO_ENERGY_DELIVERED`).** Antes dela, 7 das 10 sessões reais sem energia eram barradas pelo ML, e o síndico via só "padrão fora do histórico". Com a regra, as 10 chegam com o motivo certo: carro plugado sem receber energia, informação útil para a tarifa de ociosidade do rateio. O limite de 0,25 kWh fica entre a maior sessão real sem recarga (0,24 kWh) e a menor sessão normal real (0,75 kWh), e abaixo do piso teórico da menor anomalia dos testes automatizados (0,3 kWh: o piso de 1 kWh do gerador sintético × 30% da energia), que precisa continuar sendo detectada só pelo ML. Na prática, a menor anomalia dos testes tem 1,57 kWh e a menor da avaliação com dado real, 1,47 kWh.
- **Regra para potência média acima da máxima (`AVERAGE_EXCEEDS_MAX_POWER`).** Caso fisicamente impossível que antes dependia do ML. Usa "maior que" e não "maior ou igual": média igual à máxima é possível (sessão sem energia ou carga plana). Nenhuma das 225 sessões reais viola a regra.

## 5. Camada 3 — modelo de ML

- **Isolation Forest + LOF (PyOD), combinados por "ou".** A sessão é suspeita se qualquer um dos dois marcar. Na avaliação atual, o LOF sozinho detectou as 38 anomalias; o Isolation Forest marcou apenas 4 (de recarga lenta), todas também pegas pelo LOF, e elevou o falso alarme do treino de 4 para 6 sessões. Antes da feature de coerência, o Isolation Forest chegou a detectar uma anomalia de energia alta que o LOF não pegava. Ele foi mantido como segunda opinião para anomalias extremas não cobertas pelos cinco tipos de avaliação e por coerência com o planejado na Sprint 1; a combinação deve ser reavaliada com mais dados.
- **Score final é o maior dos dois, mas é relativo.** O score do PyOD não é uma probabilidade calibrada: ele não ordena perfeitamente as sessões (na avaliação, duas anomalias não detectadas tiveram score maior que uma detectada). A decisão é sempre o `is_anomaly`, calculado pelas linhas de corte dos modelos; o score serve como indicação de intensidade e não deve ser usado como limiar.
- **`contamination = 0.02`, por modelo.** Cada modelo coloca a linha de corte de forma que cerca de 2% das sessões de treino fiquem acima dela (4 de 172). Como a sessão é suspeita se qualquer um dos dois marcar, o sistema combinado marca cerca de 3,5% do treino (6 de 172). Na validação, com sessões futuras, a taxa observada foi de ~5%.
- **Padronização da escala (`StandardScaler`).** O LOF mede distâncias; sem padronizar, features com números maiores pesariam mais.
- **Cinco features:** duração (h), energia total (kWh), potência média (kW), potência máxima (kW) e fator de coerência.
- **Fator de coerência = energia ÷ (potência média × duração).** Nas sessões reais vale 0,90 ± 0,008. Sem ele, o modelo pegava só 1 de 8 sessões com medição incoerente (números plausíveis isoladamente, mas que não fecham entre si); com ele, 8 de 8.
- **Horário de início removido das features.** O modelo detecta anomalias de medição, não de comportamento. Além disso, o modelo de rateio incentiva recarga de madrugada (tarifa por horário); marcar essas sessões como suspeitas puniria o comportamento que o próprio sistema recomenda.
- **`card_id`, `green_kwh`, `grid_kwh` e `status` fora das features.** O `card_id` é sempre o mesmo na SEMS; green e grid refletem o defeito de instrumentação do lab; o status "desconexão anormal" aparece em sessões normais.
- **Modelo versionado (`modelo_v1.joblib`, versão `v1.0.0`).** Cada resultado registra a versão do modelo que avaliou a sessão, para auditoria.

## 6. Dados sintéticos

- **Gerador calibrado com as 215 sessões reais.** Energia 8,0 ± 3,4 kWh; potência média dependente da energia (correlação 0,39 no real); potência máxima entre 3,3 e 3,5 kW (teto de operação do carregador do lab); horário em dois grupos (88% noite, 12% dia).
- **Potência média calibrada em ~2,3 kW, não 3,0.** A estimativa inicial vinha de duas sessões; com 215, ficou claro que o carregador reduz a potência no fim da carga.
- **Uso do gerador:** testes automatizados que não dependem dos CSVs e plano B para condomínios sem histórico. O modelo é treinado com dado real, não sintético.

## 7. Avaliação

- **Anomalias de avaliação criadas a partir de sessões reais de validação**, em cinco tipos: pico alto, potência alta, energia alta, recarga lenta e medição incoerente. Todas são fisicamente possíveis (passam nas regras), para que apenas a Camada 3 possa detectá-las.
- **Resultados (`python -m condocharge_ai.training.avaliar`):**
  - Anomalias detectadas: **38 de 40 (95%)**, todas pela Camada 3.
  - Sessões reais de validação (43): 40 aprovadas, 1 barrada pela regra de atribuição e 2 barradas pelo ML. A barrada pela regra (20/08/2026, com solar e rede zerados) tem um problema real de atribuição na SEMS+ e não conta como falso alarme. Os falsos alarmes são as 2 do ML: **2 em 42 sessões normais (~5%)**. O script de avaliação imprime "3 de 43" porque soma as duas situações.
  - Sessões reais sem energia: **10 de 10 barradas pela regra `NO_ENERGY_DELIVERED`**, com o motivo correto para o síndico.

## 8. Desvios em relação à Sprint 1 e limitações

- **Gateway local e Modbus TCP:** fora do protótipo, por falta de acesso ao equipamento.
- **IA B (recomendação de horário de recarga):** não implementada nesta sprint; prioridade P1 no plano do grupo. Fica como evolução futura.
- **XGBoost e dados meteorológicos (INMET):** previstos para a IA B; não utilizados.
- **Validação com um único carregador e um único usuário simulado.** Em um condomínio real, o modelo deve ser retreinado com o histórico do próprio prédio. Para carregadores de potências diferentes, as features de potência podem ser normalizadas pela potência nominal de cada um.
- **Condomínio sem histórico ("partida a frio"):** funciona só com as Camadas 1 e 2 até acumular sessões, ou com um modelo inicial treinado em dados sintéticos.
- **Retreino exige reiniciar o processo.** O modelo é carregado uma única vez e mantido em memória (`lru_cache`). Um modelo retreinado só passa a valer depois que o backend reinicia.
- **Correção do green é uma heurística.** A regra "green maior que o dobro do total, dividir por 10" funciona para os 35 casos atuais, mas foi feita para esse erro de extração específico. Uma extração direta pela API da SEMS+ dispensaria a correção.
- **Motivos de fim desconhecidos viram falha.** Qualquer motivo da SEMS+ fora do mapeamento é tratado como `interrupted_by_failure`. Nenhuma sessão real produziu `stopped_by_user`.
- **Junção das tabelas pelo horário de início.** Os CSVs da SEMS+ não têm identificador de sessão; a lista e os detalhes são unidos pelo horário de início. Hoje as 225 sessões casam uma a uma, sem duplicatas.
- **Gerador sintético simplificado.** Limita a potência média a 3,3 kW (o real chegou a 3,38) e sorteia a divisão solar/rede, enquanto o lab registra quase tudo como solar. Não afeta o modelo, que é treinado com dado real.
- **Motivos sobrepostos.** Uma mesma sessão pode disparar mais de uma regra (ex.: término antes do início também conta como duração curta). O síndico vê todos os motivos, o que é redundante mas não incorreto.
- **Anomalia de energia alta depende da sessão base.** A fórmula (2,5 × energia da base + 5 kWh) só passa da maior sessão real (16 kWh) quando a base tem mais de ~4,5 kWh. As duas anomalias desse tipo não detectadas são justamente as de menor energia (~17 kWh). A fórmula não foi alterada para não ajustar a avaliação ao resultado do modelo.
- **Erros da Camada 1 não indicam o campo.** O código `INVALID_FIELD` não diz qual campo veio errado, embora o Pydantic forneça essa informação. Melhoria futura: incluir o nome do campo na frase para o síndico.