"""Treino do modelo de detecção de anomalias (Camada 3) com as sessões reais da SEMS+."""

import joblib
import numpy as np
from pyod.models.iforest import IForest
from pyod.models.lof import LOF
from sklearn.preprocessing import StandardScaler

from condocharge_ai import ml_model
from condocharge_ai.schemas import SessionDTO
from condocharge_ai.training.dados_reais import carregar_sessoes_reais, separar_treino_validacao

# Fração do treino aceita como estranha: define a linha de corte dos modelos
# (~2% por modelo: das 172 sessões de treino, cada um marca 4. Como a Camada 3
# combina os dois por "ou", o conjunto marca 6, ~3,5%)
CONTAMINACAO = 0.02
# Semente do Isolation Forest (aleatório); o LOF é determinístico e não precisa
SEMENTE = 42
# Gravada no pacote e devolvida em cada resultado, para auditoria. Mudou o
# treino ou as features, mude a versão.
VERSAO_MODELO = "v1.0.0"


def montar_matriz(sessoes):
    """Converte uma lista de sessões (dicionários) na matriz de features do modelo."""
    # Passa pelo SessionDTO e pela mesma extrair_features da inferência: treino e
    # uso enxergam a sessão exatamente igual
    linhas = [ml_model.extrair_features(SessionDTO.model_validate(dados)) for dados in sessoes]
    return np.array(linhas)


def treinar(sessoes_treino):
    """Treina o padronizador, o Isolation Forest e o LOF, e devolve tudo num único pacote."""
    matriz = montar_matriz(sessoes_treino)

    # O LOF mede distâncias: sem padronizar, features com números maiores
    # (energia, duração) pesariam mais que o fator de coerência (~0,9)
    escalonador = StandardScaler().fit(matriz)
    matriz_padronizada = escalonador.transform(matriz)

    iforest = IForest(contamination=CONTAMINACAO, random_state=SEMENTE).fit(matriz_padronizada)
    lof = LOF(contamination=CONTAMINACAO).fit(matriz_padronizada)

    # Tudo num dicionário só, salvo num único .joblib: escalonador e modelos
    # precisam andar juntos, já que os modelos foram treinados na escala dele
    return {
        "versao": VERSAO_MODELO,
        "nomes_features": ml_model.NOMES_FEATURES,
        "escalonador": escalonador,
        "iforest": iforest,
        "lof": lof,
    }


def main():
    """Carrega as sessões reais, treina com a parte de treino e salva o modelo."""
    # O "_" descarta o que o treino não usa: as sessões sem energia e a validação,
    # que fica reservada para o avaliar.py
    normais, _ = carregar_sessoes_reais()
    treino, _ = separar_treino_validacao(normais)

    modelo = treinar(treino)
    joblib.dump(modelo, ml_model.CAMINHO_MODELO)

    print(f"Modelo {VERSAO_MODELO} treinado com {len(treino)} sessões.")
    print(f"Salvo em: {ml_model.CAMINHO_MODELO}")


if __name__ == "__main__":
    main()