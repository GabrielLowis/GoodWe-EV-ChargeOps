"""Avaliação do sistema completo (três camadas) com sessões reais e anomalias de medição.

Avalia pela check_session, e não só pelo modelo, para medir o que o síndico
de fato veria. Usa apenas a validação (sessões mais recentes), que o modelo
nunca viu no treino.
"""

from collections import Counter

from condocharge_ai.anomaly import check_session
from condocharge_ai.training.dados_reais import carregar_sessoes_reais, separar_treino_validacao
from condocharge_ai.training.dataset import TIPOS_ANOMALIA, criar_anomalias


def contar_portas(sessoes):
    """Passa cada sessão pela check_session e conta por qual porta (layer) ela saiu."""
    resultados = [check_session(dados) for dados in sessoes]
    # Counter conta quantas vezes cada layer aparece e devolve 0 para layer
    # ausente, então contagem["ml"] funciona mesmo sem nenhuma sessão barrada no ML
    return Counter(resultado["layer"] for resultado in resultados)


def imprimir_grupo(nome, contagem):
    """Mostra quantas sessões do grupo saíram por cada porta e a fração barrada."""
    total = sum(contagem.values())
    # Um grupo pode vir vazio (ex.: um export sem sessões sem energia); sem isto,
    # a fração barrada dividiria por zero
    if total == 0:
        print(f"\n{nome}: nenhuma sessão")
        return
    barradas = total - contagem["passed"]

    print(f"\n{nome} ({total} sessões)")
    for porta in ["passed", "structural", "rules", "ml"]:
        print(f"  {porta:<11} {contagem[porta]}")
    print(f"  barradas: {barradas} de {total} ({barradas / total:.1%})")


def main():
    """Avalia o sistema com as sessões reais de validação, as anomalias e as sessões sem energia."""
    normais, sem_energia = carregar_sessoes_reais()
    _, validacao = separar_treino_validacao(normais)
    # Anomalias derivadas de sessões reais de validação, e não do gerador
    # sintético: só a grandeza alterada difere do padrão real
    anomalias = criar_anomalias(validacao)

    print("=== Avaliação do sistema CondoCharge (três camadas) ===")

    imprimir_grupo("Sessões reais de validação", contar_portas(validacao))
    imprimir_grupo("Anomalias de medição", contar_portas(anomalias))

    print("\nDetecção por tipo de anomalia:")
    for tipo in TIPOS_ANOMALIA:
        # O tipo vem codificado no session_id criado por criar_anomalia
        do_tipo = [a for a in anomalias if a["session_id"].startswith(f"ANOM-{tipo}-")]
        contagem = contar_portas(do_tipo)
        print(f"  {tipo:<20} {len(do_tipo) - contagem['passed']} de {len(do_tipo)}")

    imprimir_grupo("Sessões reais sem energia", contar_portas(sem_energia))


if __name__ == "__main__":
    main()