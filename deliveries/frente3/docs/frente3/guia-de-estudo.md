# Frente 3 
## 1. Ordem de leitura (cerca de 1h30)

| Ordem | Arquivo | O que observar | Tempo |
|---|---|---|---|
| 1 | `backend/db/enums.py` | O vocabulário: status da sessão, da reserva, da anomalia e as 3 regras de cobrança | 10 min |
| 2 | `backend/migrations/versions/0001_schema_inicial.py` | Procure "REGRA DE INTEGRIDADE": são as 5 regras do plano | 25 min |
| 3 | `backend/rateio/engine.py`, função `calculate_session` | Os 8 passos numerados no código | 20 min |
| 4 | `backend/rateio/bands.py` e `allocation.py` | Como a sessão vira trechos e como os kWh são divididos | 15 min |
| 5 | `backend/rateio/idle.py` | Tolerância de 15 min e de onde vem o fim da energia | 5 min |
| 6 | `backend/faturamento/service.py`, função `generate_invoice` | Busca no banco, chama o motor, grava a fatura | 15 min |
| 7 | `python scripts/demo_frente3.py --reset` | Rode e leia a saída de cima a baixo | 10 min |

## 2. A explicação em um minuto

> Transforma uma sessão de recarga em uma cobrança auditável. O banco, em PostgreSQL, tem as dez
> entidades do plano e garante as regras de integridade no próprio banco: uma sessão só pode ser cobrada uma vez e
> de um único morador, duas reservas não ocupam o mesmo conector no mesmo horário, e uma fatura fechada não muda nem
> com um UPDATE manual. O motor de rateio aplica o modelo híbrido da Sprint 1: divide a sessão pelas faixas horárias,
> então se a recarga começa no intermediário e termina na ponta cada trecho paga a sua tarifa; separa energia solar e
> da rede; cobra ociosidade só depois de 15 minutos; e soma imposto e overhead, que são parâmetros com vigência e não
> números fixos no código. Cada linha da fatura guarda uma memória de cálculo que reproduz o valor, o que atende à
> transparência que a LGPD exige. E a IA é estrutural: sessão marcada como anômala não entra na fatura até o síndico
> revisar, e essa revisão fica registrada.

## 3. Explicacao das escolhas

O faturamento usa `Decimal`, e não `float`, porque `float` é binário: `0.1 + 0.2` dá `0.30000000000000004`.
Em cobrança, qualquer centavo errado é injusto com alguém. `Decimal` calcula em base 10, e o banco usa `NUMERIC`.

Nas reservas, o banco usa um `EXCLUDE USING gist`, uma restrição que impede duas linhas "conflitantes".
Nesse caso, conflito significa mesmo carregador, mesmo conector e intervalos de tempo que se sobrepõem (`&&`).
Ao contrário de uma checagem em Python, essa restrição vale também quando duas requisições chegam ao mesmo tempo,
porque quem decide é o banco.

No item da fatura, a chave estrangeira para a sessão é composta: `(session_id, user_id)`. O item repete o `user_id`,
e duas FKs obrigam esse morador a ser o dono da fatura e também o dono da sessão. Junto com o `UNIQUE(session_id)`,
isso garante a regra "uma sessão não pode ser cobrada para dois moradores".

As tarifas são versionadas: cada versão tem `valid_from`/`valid_to`, e o banco impede que duas estejam vigentes
no mesmo período. Se a tarifa muda no meio do mês, cada sessão usa a versão vigente no seu início.
No cenário de demonstração, a sessão de agosto do Diego é cobrada em setembro com a tabela de agosto.

Uma fatura antiga continua reproduzível graças a três camadas: o item grava os valores, em vez de recalculá-los
na hora de mostrar; a memória de cálculo guarda uma cópia da tarifa usada; e o banco proíbe alterar tarifa ou alíquota
que já entrou em alguma fatura.

Se a SEMS e o gateway mandarem a mesma sessão, o banco recusa a segunda, porque não aceita duas sessões sobrepostas
no mesmo conector (o que seria fisicamente impossível). O backend trata essa recusa como reconciliação e registra
a divergência na auditoria.

A divisão da energia de uma sessão em trechos segue a curva de potência, e não o tempo. A potência cai no fim da carga,
e dividir pelo tempo supõe potência constante, o que joga energia demais no último trecho. A curva só define
a proporção; o total cobrado continua sendo o do medidor.

Para que as partes somem exatamente o total, o arredondamento usa o método dos maiores restos. Ao dividir 7,500 kWh
na proporção 30:40, as partes são 3,2142857... e 4,2857142... Arredondar cada uma de forma independente não garante
que a soma feche: truncando, fica 3,214 + 4,285 = 7,499. O método dá o piso a cada parte e distribui as sobras
para as maiores frações, chegando a 3,214 + 4,286 = 7,500.

A ociosidade só é cobrada quando se sabe o momento em que a energia terminou. Sem esse dado, não há como
provar que o carro ficou parado depois da carga e, na dúvida, a decisão é a favor do morador. Por isso pedimos
`energy_ended_at` à Frente 1.

O imposto também é calculado por sessão, pelo mesmo motivo das tarifas: respeitar a vigência.
Se a alíquota muda no meio do mês, cada sessão usa a sua. Como o imposto é proporcional, o resultado é o mesmo de
aplicá-lo ao subtotal do mês, a menos de centavos de arredondamento; isso está documentado como desvio justificado.

O ponto de encontro entre o faturamento e a IA é a tabela `anomalies`. Quando a Frente 4 insere uma suspeita, um
gatilho suspende a sessão, e tanto o motor quanto o banco se recusam a faturar sessão não aprovada. Na revisão,
o síndico libera ou descarta a sessão, e a decisão fica registrada na auditoria. O exemplo da demo é uma sessão
de 50 kWh em 90 minutos num carregador de 7 kW.

Em relação à LGPD, o foco é o art. 20 (revisão de decisões automatizadas): a sessão suspeita passa por revisão humana,
com responsável e data obrigatórios; a memória de cálculo explica cada centavo ao morador; e a auditoria
não pode ser apagada.

Por fim, ficaram de fora o estorno de fatura já fechada (que vira ajuste na fatura seguinte), o cálculo de ICMS
"por dentro", o multi-condomínio e o pagamento. Tudo isso está descrito na seção de limitações do README.

## 4. Três experimentos para testar o próprio entendimento

1. Em `backend/seeds/demo.py`, mude o preço Grid da ponta da versão 2 de `1.45` para `1.50` e rode
   `python -m pytest backend/tests`. Quais testes falham e por quê? Desfaça a mudança.
2. Depois da demo, abra o `psql` e tente `UPDATE invoices SET total = 0 WHERE id = 1;`. Leia a mensagem do gatilho.
3. No notebook, troque a tolerância de 15 para 10 minutos e veja a tabela de ociosidade mudar.

## 5. Sugestão de trecho para o vídeo pitch (20 a 30 segundos)

Mostrar o gráfico `evidencias/frente3/grafico_sessao_atravessando_faixas.png` e dizer:
"Esta recarga começou às 17:30, no horário intermediário, e terminou às 20:30, na ponta. O motor divide a energia
pela curva de potência: 18% no intermediário e 82% na ponta, cada parte com a sua tarifa. O carro ficou 20 minutos
parado depois da carga: 15 são de tolerância e 5 são cobrados. Tudo isso fica na memória de cálculo da fatura, que o
morador pode abrir linha por linha."

## 6. Como revisar e registrar no Git

Commits frequentes e com mensagens descritivas contam na avaliação. Uma forma natural é revisar uma parte por vez,
rodar os testes daquela parte, ajustar o que achar necessário e então fazer o commit. Ordem sugerida:

1. `feat(banco): cria schema inicial com as entidades do plano (migration 0001)`
2. `feat(banco): garante regras de integridade com EXCLUDE, FKs compostas e gatilhos`
3. `test(banco): testes de migrations e de integridade no PostgreSQL`
4. `feat(rateio): classifica faixas horárias e divide a sessão em trechos`
5. `feat(rateio): distribui kWh pela curva de potência com maiores restos`
6. `feat(rateio): ociosidade com tolerância de 15 min e casos excepcionais`
7. `feat(rateio): imposto e overhead parametrizáveis e memória de cálculo`
8. `test(rateio): casos obrigatórios do plano (faixas, tolerância, falha, imposto)`
9. `feat(fatura): gera, recalcula e fecha a fatura mensal; relatório de arrecadação`
10. `chore(seed): cenário de demonstração de setembro/2026`
11. `ci: testes da Frente 3 com PostgreSQL no GitHub Actions`
12. `docs(frente3): README, modelo de dados, motor de rateio e contratos de integração`
13. `docs(evidencias): saída da demo, dos testes e notebook executado`

