"""Camada 3: detecção de anomalias estatísticas com Isolation Forest e LOF.

Só chega aqui a sessão que já passou nas Camadas 1 e 2, ou seja, que é
fisicamente possível. O modelo responde a outra pergunta: ela se parece com
o histórico do carregador?
"""

from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np

from condocharge_ai.schemas import SessionDTO


# Só grandezas de medição. Ficam de fora:
# - hora de início: o objetivo é achar erro de medição, não comportamento, e o
#   rateio incentiva recarga de madrugada; marcar esse horário puniria o que o
#   próprio sistema recomenda;
# - card_id (sempre o mesmo na SEMS), green/grid (defeito de instrumentação do
#   lab) e status ("desconexão anormal" aparece em sessões normais).
# A ordem precisa ser a mesma de extrair_features e do treino.
NOMES_FEATURES = [
    "duracao_horas",
    "total_kwh",
    "average_power_kw",
    "max_power_kw",
    "fator_coerencia",
]

# Arquivo com o modelo treinado (gerado por training/train.py)
CAMINHO_MODELO = Path(__file__).parent / "artifacts" / "modelo_v1.joblib"

def extrair_features(sessao: SessionDTO):
    """Transforma uma sessão no vetor numérico usado pelo modelo."""
    duracao_horas = (sessao.ended_at - sessao.started_at).total_seconds() / 3600

    # Energia ÷ (potência × duração): ~0,90 em sessões reais; foge disso se a medição é incoerente
    # (fica abaixo de 1 porque parte do tempo plugado o carro não está carregando).
    # Pega números plausíveis isoladamente que não fecham entre si: sem ela o modelo
    # detectava 1 de 8 medições incoerentes; com ela, 8 de 8.
    # Denominador zero dá 0.0 em vez de divisão por zero; como o real fica em ~0,90,
    # esse valor já sai como outlier.
    denominador = sessao.average_power_kw * duracao_horas
    if denominador > 0:
        fator_coerencia = sessao.total_kwh / denominador
    else:
        fator_coerencia = 0.0

    return [
        duracao_horas,
        sessao.total_kwh,
        sessao.average_power_kw,
        sessao.max_power_kw,
        fator_coerencia,
    ]


# lru_cache guarda o retorno da primeira chamada; como a função não tem
# argumentos, maxsize=1 basta. Efeito colateral: um modelo retreinado só é
# lido de novo quando o processo reinicia (ou com carregar_modelo.cache_clear()).
@lru_cache(maxsize=1)
def carregar_modelo():
    """Carrega o modelo treinado uma única vez e confere se ele usa as features atuais."""
    modelo = joblib.load(CAMINHO_MODELO)
    # Sem esta conferência, um modelo antigo com as features em outra ordem ou
    # quantidade avaliaria sessões sem nenhum erro aparente. O lru_cache não guarda
    # exceções: enquanto o modelo estiver errado, cada chamada tenta carregá-lo de novo.
    if modelo["nomes_features"] != NOMES_FEATURES:
        raise ValueError("O modelo salvo foi treinado com outras features. Rode o training/train.py novamente.")
    return modelo


def avaliar_sessao(sessao: SessionDTO):
    """Aplica o Isolation Forest e o LOF a uma sessão e devolve o veredito da Camada 3."""
    modelo = carregar_modelo()

    # Lista dentro de lista: o scikit-learn espera uma matriz (amostras x features),
    # aqui com uma única linha. O mesmo escalonador do treino precisa ser aplicado,
    # senão as distâncias do LOF não batem com as do histórico.
    features = np.array([extrair_features(sessao)])
    padronizadas = modelo["escalonador"].transform(features)

    # No PyOD, predict devolve 1 para outlier e 0 para normal; [0] pega a única linha.
    # Combinação por "ou". Na avaliação atual, o LOF sozinho detectou as 38 anomalias;
    # o Isolation Forest fica como segunda opinião para anomalias extremas (ver DECISOES.md §5)
    suspeita_iforest = bool(modelo["iforest"].predict(padronizadas)[0])
    suspeita_lof = bool(modelo["lof"].predict(padronizadas)[0])

    # Score de 0 a 1: a opinião mais desconfiada entre os dois modelos.
    # [0, 1] = primeira linha, coluna "outlier". É uma escala relativa ao treino,
    # não uma probabilidade calibrada: a decisão vem do predict acima (corte pela
    # contaminação), não de score > 0.5.
    score = max(
        modelo["iforest"].predict_proba(padronizadas)[0, 1],
        modelo["lof"].predict_proba(padronizadas)[0, 1],
    )

    motivos = []
    if suspeita_iforest:
        motivos.append("ISOLATION_FOREST_OUTLIER")
    if suspeita_lof:
        motivos.append("LOF_OUTLIER")

    return {
        "is_anomaly": suspeita_iforest or suspeita_lof,
        "score": round(float(score), 3),
        "reasons": motivos,
        "model_version": modelo["versao"],
    }