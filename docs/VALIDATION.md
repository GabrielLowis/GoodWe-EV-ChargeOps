# Evidência da preparação integrada

Validação realizada neste computador em 08/10/2026. As evidências abaixo são da cópia integrada; não são reprodução presumida dos arquivos de evidência recebidos nos ZIPs.

| Verificação | Resultado |
|---|---|
| PostgreSQL portátil isolado | 16.15, loopback 127.0.0.1:5432, autenticação SCRAM, sem serviço Windows instalado |
| Migrations do zero | Suíte aplica downgrade/upgrade no banco exclusivo evchargeops_test |
| Schema/ORM | 16 tabelas; comparação de metadata sem divergências |
| Testes backend + banco + rateio + IA + API | 168 passaram em 8,67 s; nenhum pulado |
| Testes do cliente TypeScript | 3 passaram |
| Lint Python | ruff sem erros nos módulos ativos |
| Build frontend | tsc + Vite concluídos; artefatos locais em frontend/dist, ignorados no Git |
| Dependências npm | Instalação/lockfile concluídos, auditoria no momento da instalação: 0 vulnerabilidades reportadas |
| Treinamento ativo da IA | CSV recebido, 172 sessões de treino, v1.0.0; binário reconstruído no runtime do projeto |
| Simulação HTTP contra backend em execução | Reserva 1 → sessão 1 → fatura 1, total R$ 4,04, source=simulator |
| Navegador | Página local mostra “API e banco conectados. Modelo de anomalias: v1.0.0.” pelo proxy Vite |

Os testes cobrem restrições e gatilhos do banco, aprovação/rejeição e auditoria, tarifa por faixa/curva, feriados, regras de ociosidade, falha sem cobrança, fatura zero, late entry, proteção de fatura fechada, integridade de usuário, idempotência, disponibilidade sem expor moradores, permissões e cliente HTTP.

Uma advertência da dependência Starlette informa depreciação de httpx no TestClient. Não é falha dos testes nem do fluxo de execução; deverá ser revista em atualização futura do runtime. A advertência não foi ocultada.

## O que esta validação não comprova

- Docker/Compose preparado, mas não executado: Docker não está instalado neste computador. A comprovação atual usa o mesmo código no ambiente nativo com PostgreSQL real.
- Workflow GitHub preparado, mas não executado remotamente. Não houve commit/push ou publicação.
- Nenhuma ligação física com carregador GoodWe, SEMS real ou gateway Modbus foi testada.
- Recomendação disponível é baseline determinístico, sem modelo de regressão e backtest temporal do plano.
- As telas finais, navegação por perfil, formulários, acessibilidade dos fluxos e instalação PWA em dispositivos reais serão construídos/verificados na próxima etapa.
- O modelo de anomalias tem o regime de treinamento limitado ao HCA01 de 7 kW; métricas históricas no ZIP não se tornam automaticamente métricas do sistema completo.

## Estado local entregue

Banco, backend e Vite iniciados por scripts/start-local.ps1. Logs e ids dos serviços estão em .local, ignorada. Contas/segredos locais estão em .env, ignorado. Dados de simulação estão apenas no banco de desenvolvimento; a suíte utiliza outro banco.

Para encerrar, executar scripts/stop-local.ps1. Para iniciar novamente, scripts/start-local.ps1. Os arquivos originais dos ZIPs ficaram preservados em deliveries e docs/reference.
