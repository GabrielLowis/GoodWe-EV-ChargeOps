# CondoCharge — Frente 4: IA e Ciência de Dados

Módulo de detecção de anomalias em sessões de recarga de veículos elétricos do **CondoCharge**, plataforma de gestão de recarga compartilhada em condomínios desenvolvida no Enterprise Challenge 2026 (FIAP × GoodWe).

Antes de uma sessão entrar no rateio e na fatura do morador, o módulo verifica se os dados dela são confiáveis. Sessões suspeitas não são cobradas automaticamente: vão para a fila de revisão do síndico, com o motivo em português.

## Como funciona

Toda sessão passa por três camadas, em sequência, e para na primeira que barrar:

| Camada | Pergunta | Ferramenta | Exemplo barrado |
|---|---|---|---|
| 1. Estrutural | Os dados estão no formato certo? | Pydantic | sessão sem o campo de energia |
| 2. Regras | A sessão é fisicamente possível e houve recarga? | 9 regras determinísticas | pico de 15 kW num carregador de 7 kW |
| 3. ML | A sessão se parece com o histórico? | Isolation Forest + LOF (PyOD) | pico de 6 kW num carregador que sempre opera até 3,5 kW |

O modelo de ML foi treinado com **sessões reais do carregador GoodWe HCA G2** do laboratório da FIAP, extraídas da plataforma SEMS+.

## Resultados

Avaliação com as sessões reais mais recentes (que o modelo nunca viu) e com anomalias de medição criadas a partir delas:

| Grupo | Resultado |
|---|---|
| Anomalias de medição | **38 de 40 detectadas (95%)**, todas pela camada de ML |
| Sessões reais normais | **2 falsos alarmes em 42 sessões (~5%)** |
| Sessões reais sem energia (carro plugado sem carregar) | **10 de 10 identificadas** pela regra de sessão sem recarga |

A avaliação também encontrou uma sessão real em que a SEMS+ não atribuiu a energia nem ao solar nem à rede, barrada corretamente pela regra de atribuição. Essa sessão é a 43ª do conjunto de validação: por isso o script de avaliação mostra "3 de 43" barradas, somando o bloqueio legítimo pela regra aos 2 falsos alarmes. Detalhes e justificativas em [`DECISOES.md`](DECISOES.md).

## Como o backend usa

```python
from condocharge_ai.anomaly import check_session

resultado = check_session(dados_da_sessao)
```

**Entrada:** um dicionário com os dados da sessão (como chega da SEMS+ em JSON):

```python
{
    "session_id": "abc123",
    "charger_id": "HCA01",
    "card_id": "RFID-05",
    "started_at": "2026-09-22T21:00:00",
    "ended_at": "2026-09-23T00:50:00",
    "total_kwh": 8.0,
    "green_kwh": 8.0,
    "grid_kwh": 0.0,
    "average_power_kw": 2.3,
    "max_power_kw": 3.4,
    "status": "completed",
}
```

**Saída:**

```python
{
    "is_anomaly": False,          # True = suspender a cobrança e enviar para revisão
    "score": 0.199,               # intensidade relativa; nas camadas 1 e 2 é sempre 1.0
    "layer": "passed",            # "structural" | "rules" | "ml" | "passed"
    "reasons": [],                # códigos técnicos dos problemas
    "reasons_human": [],          # frases em português para o síndico
    "model_version": "v1.0.0",    # versão do modelo (None se o ML não chegou a rodar)
}
```

O campo `layer` indica em que camada a sessão foi barrada. Só sessões com `layer: "passed"` seguem para o rateio. **Atenção:** a decisão é o `is_anomaly`. O `score` indica a intensidade da suspeita, mas não é uma probabilidade calibrada e **não deve ser usado como limiar** (por exemplo, `score > 0.5`).

## Estrutura do projeto

```
condocharge_ai/
    schemas.py          # Camada 1: SessionDTO (Pydantic)
    rules.py            # Camada 2: regras físicas
    ml_model.py         # Camada 3: features e avaliação com o modelo treinado
    anomaly.py          # Fachada check_session (une as três camadas)
    artifacts/
        modelo_v1.joblib  # modelo treinado
    training/
        dados_reais.py  # leitura e limpeza das sessões da SEMS+
        dataset.py      # gerador sintético e anomalias de avaliação
        train.py        # treino do modelo
        avaliar.py      # avaliação do sistema completo
data/                   # CSVs exportados da SEMS+
tests/                  # testes automatizados (pytest)
DECISOES.md             # decisões técnicas e desvios da Sprint 1
```

## Como rodar

Requisito: **Python 3.12**.

```bash
# 1. Criar e ativar o ambiente virtual
py -3.12 -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux / macOS

# 2. Instalar as dependências
pip install -r requirements.txt

# 3. Rodar os testes
python -m pytest

# 4. (Opcional) Retreinar o modelo com os CSVs de data/
python -m condocharge_ai.training.train

# 5. (Opcional) Reproduzir a avaliação
python -m condocharge_ai.training.avaliar
```

Os testes não dependem dos CSVs: usam dados sintéticos calibrados com as sessões reais. O treino e a avaliação precisam dos CSVs na pasta `data/`.

## Limitações e próximos passos

- Validado com um único carregador e um único usuário simulado. Em um condomínio real, o modelo deve ser retreinado com o histórico do próprio prédio.
- A recomendação de horário de recarga (IA B, prevista na Sprint 1) fica como evolução futura.
- Sem acesso físico ao equipamento, o gateway local com Modbus TCP não foi implementado; os dados vêm da SEMS+.

   Mais detalhes em [`DECISOES.md`](DECISOES.md). O uso de ferramentas de IA no desenvolvimento está descrito em [`USO_DE_IA.md`](USO_DE_IA.md).
