# Frente 3 - Motor de rateio

Implementa o **modelo híbrido** definido na Sprint 1 (README, seção 6): cobrança por energia consumida (kWh),
separada em Green e Grid e precificada pela faixa horária, mais tarifa de ociosidade. Código em `backend/rateio/`.

## 1. Onde o motor entra no fluxo

```
SEMS / gateway -> SessionDTO -> charging_sessions -> atribuição (reserva) -> validação e anomalia (Frente 4)
    -> [MOTOR DE RATEIO] -> invoice_items (memória de cálculo) -> invoices -> app do morador e painel do síndico
```

O motor é uma função pura: `calculate_session(sessão, tarifa, impostos, feriados, fuso)` devolve as cinco parcelas e
a memória de cálculo, sem acessar banco ou rede. Quem busca os dados e grava o resultado é o serviço
`backend/faturamento/service.py`. Isso deixa toda a regra financeira testável sem PostgreSQL.

## 2. Fórmula (por sessão)

| Parcela | Cálculo |
|---|---|
| Energia Green | soma, em cada trecho, de kWh Green do trecho x preço Green da faixa do trecho |
| Energia Grid | soma, em cada trecho, de kWh Grid do trecho x preço Grid da faixa do trecho |
| Ociosidade | max(0, minutos completos após o fim da energia - 15) x taxa por minuto |
| **Subtotal** | Green + Grid + Ociosidade |
| Imposto | subtotal x alíquota, uma linha por imposto vigente (a base pode excluir a energia Green) |
| Overhead | subtotal x percentual definido pela assembleia (pode ser 0%) |
| **Total** | Subtotal + Imposto + Overhead |

A fatura mensal é a soma das sessões válidas do morador. Cada parcela é arredondada ao centavo em cada sessão
(meio para cima), então a soma das linhas fecha exatamente com o total da fatura.

## 3. Passo a passo do algoritmo

`backend/rateio/engine.py`, função `calculate_session`:

1. **Recusa o que não pode ser cobrado** (`check_billable`): sessão sem morador, não aprovada, em andamento, sem fuso
   horário, com Green + Grid diferente do total (tolerância de 0,05 kWh) ou com energia fisicamente impossível
   (mais que potência nominal x tempo x 1,05). É defesa em profundidade: essas sessões nem deveriam chegar aqui.
2. **Escolhe a regra de cobrança** pelo encerramento: `completed` -> `normal`; `user_stopped` ->
   `user_stopped_no_idle`; `system_failure` -> `system_failure_no_charge` (linha zerada, com o motivo).
3. **Descobre o fim do fluxo de energia** (`idle.py`): informado pela fonte; se não vier, estimado pela curva de
   potência (primeira leitura sem fluxo); se também não houver curva, fica desconhecido e não se cobra ociosidade.
4. **Divide o intervalo de carga em trechos de faixa** (`bands.py`, `split_by_band`): converte para o horário local,
   anda de fronteira em fronteira (início/fim de cada janela e meia-noite) e une trechos vizinhos da mesma faixa.
   Fim de semana e feriado são fora de ponta o dia todo.
5. **Distribui os kWh medidos entre os trechos** (`allocation.py`): pela curva de potência, se ela cobrir ao menos
   90% da carga; senão, proporcional ao tempo. Os kWh de cada trecho são arredondados a 1 Wh pelo método dos maiores
   restos, e a soma dos trechos fecha exatamente com o total medido.
6. **Valoriza** cada trecho com o preço Green e Grid da sua faixa e arredonda Green e Grid ao centavo.
7. **Ociosidade** (somente regra `normal`), **subtotal**, **impostos** e **overhead**.
8. **Monta a memória de cálculo** (JSON) com a cópia da tarifa usada, os trechos e um texto explicativo.

## 4. Sessão que atravessa faixas (caso obrigatório do plano)

Exemplo do plano: carga das 17:30 às 20:30 de uma segunda-feira. Faixas de demonstração: intermediário 17-18h e
21-22h, ponta 18-21h. Preços Grid fictícios: intermediário R$ 0,95, ponta R$ 1,45.

**Sem curva de potência (proporcional ao tempo)**, 19,8 kWh da rede:

| Trecho | Minutos | Fração | kWh Grid | Preço | Valor |
|---|---|---|---|---|---|
| 17:30-18:00 intermediário | 30 | 1/6 | 3,300 | R$ 0,95 | R$ 3,1350 |
| 18:00-20:30 ponta | 150 | 5/6 | 16,500 | R$ 1,45 | R$ 23,9250 |
| **Energia da rede** | | | 19,800 | | **R$ 27,06** |

Carro desconectado às 20:50: 20 min - 15 de tolerância = 5 min x R$ 0,25 = R$ 1,25. Subtotal R$ 28,31;
ISS 5% = 1,4155 -> R$ 1,42; overhead 5% = R$ 1,42; **total R$ 31,15** (teste
`test_exemplo_do_plano_calculado_por_faixa`). Se a sessão inteira fosse cobrada como intermediário, a energia da rede
daria R$ 18,81: é exatamente o erro que o plano pede para evitar.

**Com curva de potência** (sessão S8 do cenário de demonstração: 19,2 kWh, 0,6 Green, 18,6 Grid, leitura a cada
5 min e queda de potência no fim da carga): a integral da curva dá 17,9% da energia no intermediário e 82,1% na
ponta, em vez de 1/6 e 5/6. Resultado: Grid R$ 25,30 (contra R$ 25,42 pelo tempo). A curva só define a proporção;
o total cobrado continua sendo o kWh medido.

### Por que o método dos maiores restos

Dividir 7,500 kWh na proporção 30:40 dá 3,2142857... e 4,2857142... Arredondando cada parte, a soma poderia virar
7,499 ou 7,501 kWh e o morador pagaria por energia que não existiu. O método dá a cada trecho o piso da sua cota em Wh
e distribui as unidades que sobram para as maiores frações: 3,214 + 4,286 = 7,500 exatos.

### Green e Grid por trecho

A SEMS informa Green e Grid por sessão, não por trecho. Se as amostras da curva trouxerem `green_power_kw`, o motor
distribui Green e Grid pelas respectivas curvas. Senão, aplica a mesma proporção aos dois. É uma aproximação
registrada: a parte solar tende a se concentrar nos trechos com sol. A Frente 1 precisa confirmar se a SEMS expõe a
separação por intervalo (decisão em aberto nº 3 do plano).

## 5. Ociosidade

| Minutos na vaga após o fim da energia | Cobrado |
|---|---|
| 14 | R$ 0,00 |
| 15 | R$ 0,00 |
| 15 min 59 s | R$ 0,00 (só minutos completos) |
| 16 | 1 min |
| sessão encerrada pelo morador ou falha do sistema | R$ 0,00 (regra da Sprint 1) |
| fim da energia desconhecido | R$ 0,00 (sem dado, não há como provar a ociosidade) |

## 6. Casos excepcionais da Sprint 1 (seção 6.4)

| Caso | Regra da Sprint 1 | Implementação | Teste |
|---|---|---|---|
| Sessão interrompida por falha do sistema | não há cobrança; fica registrada | regra `system_failure_no_charge`: linha de R$ 0,00 com código da falha e kWh entregues; `CHECK` no banco | `test_falha_do_sistema_gera_linha_zerada_com_motivo` |
| Sessão encerrada pelo morador | paga só a energia entregue; sem ociosidade | regra `user_stopped_no_idle` | `test_encerrada_pelo_morador_paga_so_a_energia` |
| Morador que não carregou | fatura zero, sem mínimo | fatura gerada com R$ 0,00 e nota explicativa | `test_fatura_zero_para_quem_nao_carregou` |
| Dois veículos da mesma unidade | duas faturas separadas | fatura por morador (`UNIQUE (user_id, period)`), não por unidade | `test_dois_veiculos_da_mesma_unidade_geram_duas_faturas` |
| No-show de reserva | consequência comportamental, não financeira | sem sessão não há cobrança; status `no_show` e `users.reservation_blocked_until` no banco (regra de bloqueio é do backend) | seed: reserva `no_show` da Carla |

## 7. Imposto e overhead

- O imposto é uma linha da tabela `tax_rules` com tipo, jurisdição, alíquota e vigência. Podem valer vários ao mesmo
  tempo (transição IBS/CBS). Cada sessão usa as regras vigentes no seu início.
- `exclude_compensated_energy = true` tira a energia Green da base de cálculo daquele imposto. Fica desligado por
  padrão e só deve ser ligado quando a modalidade de geração permitir (Frente 2: LC 214/2025, art. 28, e
  Decreto 12.955/2026, art. 15, com as vedações do art. 15, §2º).
- O imposto é calculado "por fora" (percentual sobre a base). É uma simplificação do MVP: o ICMS real é calculado
  "por dentro". O plano pede para não transformar o sistema em um motor tributário completo.
- O overhead incide sobre o subtotal e não entra na base do imposto, na leitura literal da Sprint 1 ("sobre o
  subtotal incidem dois acréscimos"). Se o grupo decidir o contrário, é uma linha em `_taxes`.

## 8. Arredondamento e tipos

- Dinheiro e energia usam `Decimal` (nunca `float`) e `NUMERIC` no banco.
- kWh com 3 casas (1 Wh); preços com 4 casas; valores intermediários na memória com 6 casas.
- Cada parcela da sessão é arredondada ao centavo com `ROUND_HALF_UP`. A fatura soma parcelas já arredondadas.

## 9. Memória de cálculo (JSON em `invoice_items.calculation`)

| Chave | Conteúdo |
|---|---|
| `engine_version` | versão do motor que calculou (hoje `1.0.0`) |
| `session` | horários no fuso local, origem do fim da energia, kWh total/Green/Grid, potência do carregador |
| `rule` | regra aplicada e sua justificativa |
| `tariff` | cópia completa da versão da tarifa usada (preços, janelas, ociosidade, overhead) |
| `band_split` | método (`power_curve` ou `time_proportional`) e cada trecho: horário, faixa, tipo de dia, kWh, preços e valores |
| `components` | Green, Grid, ociosidade, subtotal, impostos (base, alíquota, valor), overhead e total, com as fórmulas |
| `explanation` | frases prontas para o app do morador ("Trecho 1: 21/09 17:30-18:00 (Intermediário...") |
| `notes` | observações (ex.: diferença de arredondamento da SEMS, divisão estimada pelo tempo) |

Com essa memória é possível refazer o cálculo na mão. O teste `test_toda_memoria_de_calculo_reproduz_o_valor_gravado`
faz isso para todas as linhas geradas no cenário de demonstração. Exemplo completo:
`evidencias/frente3/fatura_ana_2026-09.json`.

## 10. Conferência manual do cenário de setembro/2026

Tarifa versão 2 (a partir de 01/09): Green R$ 0,30 em todas as faixas; Grid R$ 0,65 fora de ponta, R$ 0,95
intermediário e R$ 1,45 ponta; ociosidade R$ 0,25/min; overhead 5%. Versão 1 (até 31/08): Green R$ 0,25; Grid
R$ 0,60 / 0,90 / 1,40; ociosidade R$ 0,20/min; overhead 3%. ISS 5%. Tudo fictício.

| Sessão | Morador | Situação | Green | Grid | Ocios. | Subtotal | Imposto | Overhead | Total |
|---|---|---|---|---|---|---|---|---|---|
| S0 | Diego | 28/08, lançamento posterior com a tarifa v1 | 0,00 | 12,68 | 0,00 | 12,68 | 0,63 | 0,38 | 13,69 |
| S1 | Ana | feriado de 07/09: fora de ponta o dia todo | 0,30 | 5,20 | 0,00 | 5,50 | 0,28 | 0,28 | 6,06 |
| S2 | Ana | 14 min na vaga: dentro da tolerância | 3,75 | 3,58 | 0,00 | 7,33 | 0,37 | 0,37 | 8,07 |
| S3 | Diego | 16 min na vaga (fim da energia pela curva) | 1,80 | 6,18 | 0,25 | 8,23 | 0,41 | 0,41 | 9,05 |
| S4 | Bruno | encerrada pelo morador: sem ociosidade | 0,00 | 5,84 | 0,00 | 5,84 | 0,29 | 0,29 | 6,42 |
| S5 | Diego | falha do sistema | 0,00 | 0,00 | 0,00 | 0,00 | 0,00 | 0,00 | 0,00 |
| S6 | Diego | 50 kWh em 90 min (7 kW): rejeitada na revisão | - | - | - | - | - | - | não cobrada |
| S7 | - | sem reserva correspondente | - | - | - | - | - | - | não cobrada |
| S8 | Ana | exemplo do plano, curva de potência | 0,18 | 25,30 | 1,25 | 26,73 | 1,34 | 1,34 | 29,41 |
| S9 | Bruno | SessionDTO do plano, sem fim de energia | 1,26 | 14,96 | 0,00 | 16,22 | 0,81 | 0,81 | 17,84 |

Faturas: **Ana R$ 43,54**, **Bruno R$ 24,26**, **Carla R$ 0,00**, **Diego R$ 22,74**. Total arrecadado R$ 90,54,
sendo R$ 81,03 de energia (reembolso ao condomínio). Balanço de energia das sessões de setembro: 144,8 kWh entregues =
84,0 faturados + 4,3 de falha + 50,0 rejeitados + 6,5 sem atribuição.

Exemplo de conta (S4, 21:30-22:40 de sexta, 7,5 kWh da rede, sem curva): 30 min no intermediário e 40 min fora de
ponta -> 7,5 x 30/70 = 3,214 kWh e 4,286 kWh (maiores restos) -> 3,214 x 0,95 + 4,286 x 0,65 = 3,0533 + 2,7859 =
R$ 5,84. ISS 5% de 5,84 = 0,292 -> R$ 0,29; overhead R$ 0,29; total R$ 6,42.
