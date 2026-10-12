# Validação da instalação e preparação da entrega

Conferência de **12/10/2026, São Paulo**, específica para primeira instalação, documentação e pacote acadêmico. O histórico funcional no banco dos autores continua em [RESOLUCAO-OVERVIEW](../frontend/RESOLUCAO-OVERVIEW.md). As duas superfícies têm bancos e valores diferentes.

## Instalação isolada

Foi criada uma cópia somente dos arquivos candidatos ao repositório em `.local/validacao-entrega`. Ela começou sem `.env`, banco, `.venv`, `node_modules` ou modelo ativo. Configuração nova, Python virtual e dependências foram preparados, com `pip install -r requirements.txt` e `npm ci`. Downloads usaram caches dos gerenciadores quando disponíveis; não foi copiado o ambiente instalado dos autores.

Os binários PostgreSQL 16.15 já disponíveis foram reutilizados **como runtime**, com cluster novo e exclusivo. Não foi instalado serviço Windows. Banco de demonstração `evchargeops_entrega` e banco descartável `evchargeops_entrega_test`, ambos em 55432; API em 18000 e frontend em 15173. Bootstrap aplicou a migration existente e recompôs o modelo v1.0.0 dos CSVs, com 172 sessões de treinamento. A instalação local verifica Windows; a CI abaixo acrescenta testes/build em Ubuntu com serviço PostgreSQL. Não se validou o Compose completo nem equipamento físico.

| Verificação | Resultado observado |
|---|---|
| Instalação Python e npm pelo manifest/lockfile | Concluída em ambientes novos |
| Banco, bootstrap e modelo | Migration 0001_schema_inicial; modelo v1.0.0 reconstruído |
| Saúde direta e pelo proxy Vite | HTTP 200, status/banco OK |
| Login HTTP dos dois perfis | Síndico manager e morador resident |
| Restrição da fila de anomalias | Morador recebeu 403 esperado; síndico consultou a fila |
| Simulador existente | Uma execução; reserva #1 → sessão #1 → fatura #1 |
| Sessão / vínculo financeiro | 6,2 kWh; origem simulator; incluída no item da fatura |
| Fatura de outubro de 2026 | Aberta, R$ 4,61; relatório de mesmo período consultado |
| Testes Python existentes | **186 aprovados**, nenhum pulado; um aviso existente Starlette/httpx |
| Testes frontend | **50 aprovados em 12 arquivos** |
| Build frontend | TypeScript e Vite concluídos |
| Lint Python | All checks passed |
| Reprodução dos contratos na cópia temporária | OpenAPI e tipos gerados idênticos ao commit, normalizando somente CRLF/LF |
| Navegador da cópia nova | Login/saída dos dois perfis, recarga, vínculo, memória expandida e relatório financeiro conferidos |

O total R$ 4,61 é resultado desta execução, não um valor fixo do protótipo. A sessão começou às 21h01 e atravessou faixas; a fatura mostrou Green R$ 0,30, Grid R$ 3,89, subtotal R$ 4,19, imposto R$ 0,21 e operacional R$ 0,21. O banco novo não recebeu o feriado demonstrativo cadastrado no banco dos autores. As capturas históricas com R$ 4,04 continuam válidas para o conjunto anterior.

Nenhum novo fechamento, cenário de anomalia ou edição de medição foi executado nesta preparação. O simulador pode revisar uma anomalia se necessária; a única execução foi preservada e as consultas foram retomadas sem repetir POSTs de domínio. O verificador foi ajustado para o 403 esperado e para o campo `period` do contrato de fatura. Logs de terminal de bootstrap/simulador perderam acentos em algumas mensagens; os dados do relatório são confirmados por JSON HTTP e interface, não pela grafia desses logs.

## Evidências desta conferência

Artefatos sanitizados em [evidence/entrega-academica](evidence/entrega-academica/):

- [API e dados da nova demonstração](evidence/entrega-academica/demo-verification.json).
- [Testes Python](evidence/entrega-academica/backend-tests.txt), [frontend](evidence/entrega-academica/frontend-tests.txt), [build](evidence/entrega-academica/frontend-build.txt) e [lint](evidence/entrega-academica/lint.txt).
- [Navegação observada](evidence/entrega-academica/browser-checks.json) e [console](evidence/entrega-academica/browser-console.json).
- Capturas: [início do morador](evidence/entrega-academica/01-morador-inicio.png), [sessão](evidence/entrega-academica/02-morador-sessao.png), [fatura/memória](evidence/entrega-academica/03-morador-fatura.png), [início do síndico](evidence/entrega-academica/04-sindico-inicio.png) e [financeiro](evidence/entrega-academica/05-sindico-financeiro.png).

## Publicação e pacote

O repositório **[GabrielLowis/GoodWe-EV-ChargeOps](https://github.com/GabrielLowis/GoodWe-EV-ChargeOps)** foi criado público, com branch principal `main`. Página, metadados e README responderam HTTP 200 sem autenticação. O HEAD local foi comparado ao remoto. [Registro de acesso público](evidence/entrega-academica/public-access.json).

A **[CI de publicação](https://github.com/GabrielLowis/GoodWe-EV-ChargeOps/actions/runs/38320595895)** concluiu com sucesso os jobs backend e frontend em Ubuntu: instalação, treino, testes, lint, build e conferência dos contratos. [Resultado com SHA e jobs](evidence/entrega-academica/github-actions.json). Esse registro identifica a revisão verificada; o manifesto local da entrega registra o commit final e o resultado do workflow correspondente, conferidos após o último envio.

`entrega/ENTREGA.txt` contém somente o link real. `entrega/EV-ChargeOps.zip` é produzido por `git archive`, com uma pasta superior `GoodWe-EV-ChargeOps/`, e foi extraído para conferência de CRC, conteúdo e hashes. README, código, dependências, CSVs e evidências estão presentes; somente arquivos do commit entram no ZIP. Banco, segredos, ambientes, node_modules, builds e a própria pasta de saída ficam excluídos. O binário original recebido da Frente 4 permanece em deliveries como referência; o artefato ativo é reconstruído na instalação.

`entrega/manifesto.json` fica fora do ZIP e registra commit final, tamanho, SHA-256, contagem de arquivos e CI correspondente. Assim o manifesto não precisa incluir seu próprio hash no pacote. A extração final é repetida após consolidar esta documentação.

Foram comparados **245 arquivos de código/dados/entregas/scripts/infraestrutura/testes e referências originais**, sem mudança, e **1.788 arquivos locais originais**, incluindo configuração, lista de senhas, estado dos serviços e cluster, sem mudança. Os três serviços da cópia isolada foram encerrados. [Preservação](evidence/entrega-academica/preservation.json), [links dos documentos](evidence/entrega-academica/links.json) e [conferência dos arquivos publicáveis](evidence/entrega-academica/publication-scan.json).

Commits reais registram a base recebida, a orientação acadêmica, a validação isolada e a conferência da publicação. Não houve reconstrução artificial de histórico anterior. O enunciado original continua em sua forma recebida e as referências da Sprint 01/deliveries foram preservadas.

## Limites e pendências humanas

Docker não está instalado e não foi validado. A execução nativa não comprova telemetria GoodWe/SEMS/Modbus, pagamentos, instalação PWA em aparelho ou aprovação/atribuição órfã pela interface. O histórico desta cópia começa com a base recebida; mensagens descritivas novas não comprovam a frequência de commits anterior.

O TXT e o ZIP são arquivos de entrega; envio na plataforma da faculdade, compreensão de cada integrante e pitch individual de 5 minutos continuam sendo ações humanas. Consulte [ENTREGA-ACADEMICA](ENTREGA-ACADEMICA.md).
