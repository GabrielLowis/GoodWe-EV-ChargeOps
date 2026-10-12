"""Fachada do módulo de IA: aplica as três camadas de verificação a uma sessão de recarga.

A ordem vai do mais barato e mais certo (formato, física) para o mais caro e
mais incerto (ML), parando na primeira camada que barrar. Assim o síndico
recebe o motivo mais preciso e o modelo não é consultado à toa.
"""

from pydantic import ValidationError

from condocharge_ai.schemas import SessionDTO
from condocharge_ai import ml_model, rules

# Frases exibidas ao síndico na fila de revisão, uma para cada código de problema
DESCRICOES_MOTIVOS = {
    "MISSING_FIELD": "Campo obrigatório ausente nos dados da sessão.",
    "INVALID_FIELD": "Campo com formato ou valor inválido nos dados da sessão.",
    "INVALID_TIMESTAMP": "A sessão termina antes ou no mesmo instante em que começa.",
    "NEGATIVE_KWH": "Energia negativa registrada na sessão.",
    "DURATION_TOO_SHORT": "Sessão com menos de 1 minuto registrou energia.",
    "UNKNOWN_CHARGER": "Carregador não cadastrado no condomínio.",
    "POWER_EXCEEDS_NOMINAL": "Potência máxima acima da capacidade do carregador.",
    "KWH_EXCEEDS_CAPACITY": "Energia acima do que o carregador consegue entregar no tempo da sessão.",
    "ENERGY_SOURCE_ATTRIBUTION_MISMATCH": "Energia solar + rede não corresponde ao total; verificar a medição antes do rateio.",
    "ISOLATION_FOREST_OUTLIER": "Padrão de medição muito diferente do histórico do condomínio.",
    "LOF_OUTLIER": "Padrão de medição isolado em relação às sessões mais parecidas.",
    "NO_ENERGY_DELIVERED": "Carro plugado sem receber energia: vaga ocupada sem recarga.",
    "AVERAGE_EXCEEDS_MAX_POWER": "Potência média registrada maior que a potência máxima; verificar a medição.",
}


def montar_resultado(layer, reasons, score, model_version):
    """Monta o resultado da verificação no formato combinado com o backend.

    O formato é o mesmo em todas as saídas, para o backend nunca precisar
    tratar casos diferentes. is_anomaly sai de layer: só "passed" vai para o rateio.
    """
    # .get(codigo, codigo): se um código novo ainda não tiver frase, o síndico
    # vê o próprio código em vez de o sistema quebrar
    return {
        "is_anomaly": layer != "passed",
        "score": score,
        "layer": layer,
        "reasons": reasons,
        "reasons_human": [DESCRICOES_MOTIVOS.get(codigo, codigo) for codigo in reasons],
        "model_version": model_version,
    }


def check_session(dados):
    """Verifica uma sessão nas três camadas e devolve o veredito no formato do contrato.

    É a única função que o backend chama. Sessão com is_anomaly=True não é
    cobrada: vai para a revisão do síndico (direito de revisão, LGPD art. 20).
    """

    # Camada 1: validação estrutural
    # Score 1.0 nas Camadas 1 e 2: formato errado e física impossível são certeza,
    # não suspeita. model_version None indica que o ML não chegou a rodar.
    try:
        sessao = SessionDTO.model_validate(dados)
    except ValidationError as erro:
        # O Pydantic gera um erro por campo; aqui eles viram só dois códigos,
        # sem repetição e na ordem em que apareceram
        codigos = []
        for problema in erro.errors():
            if problema["type"] == "missing":
                codigo = "MISSING_FIELD"
            else:
                codigo = "INVALID_FIELD"
            if codigo not in codigos:
                codigos.append(codigo)
        return montar_resultado("structural", codigos, 1.0, None)
    
    # Camada 2: regras de plausibilidade física
    violacoes = rules.verificar_regras(sessao)
    if violacoes:
        return montar_resultado("rules", violacoes, 1.0, None)
    
    # Camada 3: modelo de ML
    # Mesmo aprovada, a sessão leva o score e a versão do modelo, para auditoria
    resultado_ml = ml_model.avaliar_sessao(sessao)
    if resultado_ml["is_anomaly"]:
        camada = "ml"
    else:
        camada = "passed"
    return montar_resultado(
        camada,
        resultado_ml["reasons"],
        resultado_ml["score"],
        resultado_ml["model_version"],
    )