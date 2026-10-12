# Guia do codigo (para estudar e explicar)

O enunciado exige que o grupo saiba explicar qualquer trecho entregue. Este guia mostra por onde ler e o que dizer.

## Ordem de leitura

1. `schemas.py` - o `SessionDTO` (contrato que voce ja escreveu).
2. `models.py` - as tabelas. Veja `ChargingSession.user_id` e `processing_status`: o primeiro diz de quem e a
   sessao, o segundo diz em que etapa do pipeline ela esta.
3. `services/pipeline.py` - `ingest_session`: o coracao do back-end (atribuir, validar, decidir o destino).
4. `ai/rules.py` e `ai/anomaly.py` - as camadas de validacao.
5. `services/rateio.py` - o calculo. Comece por `calculate_charge` e leia as funcoes que ela chama.
6. `services/billing.py` - transforma sessoes aprovadas em fatura.
7. `routers/` - so recebem a requisicao, chamam os services e devolvem a resposta.
8. `tests/` - cada teste descreve uma regra de negocio; sao a melhor documentacao do comportamento.

## O que acontece quando uma sessao chega (POST /sessoes)

1. O FastAPI valida o JSON contra o `SessionDTO` (formato).
2. O router confere se o carregador existe (422) e se a sessao ja foi cadastrada (409).
3. `ingest_session` grava a sessao e procura uma reserva `Await` do carregador cuja janela contem `started_at`.
   Achou: preenche `reservation_id` e `user_id` e marca a reserva como `Completed`.
4. `check_session` roda as camadas e para na primeira que falhar.
5. Sem morador, ou com falha na validacao: cria uma `Anomaly` pendente (fila do sindico).
   Caso contrario: a sessao fica `Approved`.
6. Tudo e registrado em `audit_events`. O `commit` grava de uma vez so.

## Como o rateio calcula

1. Divide a sessao em trechos, um por faixa tarifaria atravessada (`split_segments`).
2. Distribui a energia Green e Grid entre os trechos proporcionalmente ao tempo.
3. Soma `energia x tarifa` de cada trecho.
4. Estima a ociosidade e cobra so o que passa de 15 minutos (`billable_idle_minutes`).
5. `subtotal = green + grid + ociosidade`; imposto e overhead incidem sobre o subtotal.
6. Guarda tudo na memoria de calculo (JSON) do item da fatura.

## Perguntas que o professor pode fazer

- Por que dinheiro em `Decimal` e nao em `float`? (`float` acumula erro de arredondamento binario.)
- Por que o rateio e feito de funcoes puras? (Sem banco, e testavel e facil de explicar.)
- Por que existe `processing_status` alem de `status`? (`status` vem do carregador; `processing_status` e do nosso pipeline.)
- O que impede cobrar a mesma sessao duas vezes? (`unique=True` em `InvoiceItem.session_id` e o status `Billed`.)
- Como uma fatura antiga continua reproduzivel? (Memoria de calculo com os parametros usados e tarifas versionadas.)
- Por que a sessao sem reserva nao vai para o dono do cartao? (O cartao e compartilhado; o sindico decide.)
- O que a Dependency (`Depends(get_db)`) faz? (Abre uma session por requisicao e fecha no final, mesmo com erro.)
