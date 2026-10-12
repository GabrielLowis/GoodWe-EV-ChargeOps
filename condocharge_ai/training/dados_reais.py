"""Leitura das sessões reais do HCA G2 exportadas da SEMS+.

Os CSVs cobrem só a fase de uso regular (mesmo cartão, recarga noturna quase
diária). A fase de comissionamento do instalador foi descartada por ser outro
regime de uso.
"""

import glob
from pathlib import Path

import pandas as pd

from condocharge_ai.rules import ENERGIA_MINIMA_RECARGA_KWH

# Pasta com os CSVs exportados da SEMS+, na raiz do projeto (calculada a partir deste arquivo)
# Três .parent sobem de training/dados_reais.py até a raiz; assim treino e
# avaliação funcionam de qualquer diretório, como já acontece com CAMINHO_MODELO.
PASTA_DADOS = Path(__file__).parent.parent.parent / "data"


# Texto do motivo de fim na SEMS+ -> SessionStatus. Motivos fora desta lista
# caem em "interrupted_by_failure" (ver linha_para_sessao).
MOTIVO_PARA_STATUS = {
    "Charging stopped at full charge": "completed",
    "Abnormal disconnection of charging gun from vehicle.": "abnormal_disconnection",
    "Generation Loss": "interrupted_by_failure",
}


def carregar_tabela_real(pasta=PASTA_DADOS):
    """Lê os CSVs da SEMS+ e junta a lista básica (Etapa A) com os detalhes (Etapa B)."""
    lista = pd.read_csv(f"{pasta}/etapa_a_sessoes_fase_morador.csv")

    # Etapa B vem num CSV por mês; o horário de início é a chave comum entre as
    # duas etapas (os CSVs não têm coluna de id de sessão)
    arquivos_detalhe = sorted(glob.glob(f"{pasta}/etapaB_detalhe_*.csv"))
    detalhes = pd.concat([pd.read_csv(arquivo) for arquivo in arquivos_detalhe])

    tabela = lista.merge(detalhes, on="inicio")
    return tabela


def linha_para_sessao(linha, indice):
    """Converte uma linha da tabela real num dicionário no formato do SessionDTO."""
    total_kwh = linha["energia_total_kwh"]

    # Correção de extração: 35 sessões vieram com o green 10x maior (vírgula decimal lida errado)
    # (ex.: total 5,2 kWh, green 52,0). O green nunca pode passar do total, então
    # "mais que o dobro" separa com folga o erro de extração do arredondamento normal.
    green_kwh = linha["green_kwh"]
    if green_kwh > 2 * total_kwh:
        green_kwh = green_kwh / 10

    return {
        "session_id": f"REAL-{indice:04d}",
        "charger_id": "HCA01",
        "card_id": linha["card_id"],
        "started_at": linha["inicio"],
        "ended_at": linha["fim"],
        "total_kwh": total_kwh,
        "green_kwh": green_kwh,
        "grid_kwh": linha["importada_kwh"],
        "average_power_kw": linha["potencia_media_kw"],
        "max_power_kw": linha["potencia_maxima_kw"],
        "status": MOTIVO_PARA_STATUS.get(linha["motivo_fim"], "interrupted_by_failure"),
    }


def carregar_sessoes_reais(pasta=PASTA_DADOS):
    """Devolve as sessões reais com recarga e, separadas, as sessões sem energia entregue."""
    tabela = carregar_tabela_real(pasta)

    # As sessões sem energia não treinam o modelo (não são recargas), mas
    # servem de caso real na avaliação
    sessoes = []
    sessoes_sem_energia = []
    # iterrows percorre o DataFrame linha a linha, devolvendo (índice, linha);
    # a linha é uma Series acessada pelo nome da coluna. É lento, mas com 225
    # sessões a clareza compensa.
    for indice, linha in tabela.iterrows():
        dados = linha_para_sessao(linha, indice)
        if linha["energia_total_kwh"] > ENERGIA_MINIMA_RECARGA_KWH:
            sessoes.append(dados)
        else:
            sessoes_sem_energia.append(dados)

    return sessoes, sessoes_sem_energia


def separar_treino_validacao(sessoes, fracao_treino=0.8):
    """Separa as sessões em treino (mais antigas) e validação (mais recentes), por ordem cronológica.

    Separação temporal, e não aleatória, para simular o uso real: o modelo
    treina com o histórico e é aplicado a sessões futuras. Com 215 sessões e
    fração 0.8: 172 de treino e 43 de validação (a partir de 23/07/2026).
    """
    # started_at ainda é texto "AAAA-MM-DD HH:MM:SS"; nesse formato a ordem
    # alfabética coincide com a cronológica
    ordenadas = sorted(sessoes, key=lambda s: s["started_at"])
    corte = int(len(ordenadas) * fracao_treino)
    return ordenadas[:corte], ordenadas[corte:]