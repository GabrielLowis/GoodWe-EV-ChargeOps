# Frente 5 — contexto e base de desenvolvimento

Escopo lido nas páginas 8–9 do plano da Sprint 2. As duas experiências usam a mesma API e a autorização é aplicada pelo backend. As telas das entregas 1–4 estão implementadas em React/TypeScript/Vite, com cliente gerado de OpenAPI, autenticação em memória, navegação por perfil e infraestrutura PWA. Consulte frontend/RESOLUCAO-OVERVIEW.md para a validação funcional de 12/10 e docs/VALIDACAO-ENTREGA.md para a instalação/pacote; frontend/VALIDACAO-FINAL.md é histórico de 11/10. A tabela abaixo descreve contratos disponíveis; o pacote implementado segue docs/ENTREGAS-FRENTE5.md.

## Morador

| Tela prevista | API pronta para uso |
|---|---|
| Login | POST /api/login; GET /api/usuarios/eu |
| Home | GET /api/reservas; GET /api/sessoes; GET /api/faturas (somente dados próprios) |
| Reservar | GET /api/carregadores; GET /api/carregadores/{id}/disponibilidade; POST /api/reservas; POST /api/reservas/{id}/cancelar |
| Recomendação | GET /api/recomendacao-janela?charger_id=...&kwh=...&power_kw=... |
| Histórico de sessões | GET /api/sessoes; GET /api/sessoes/{id} |
| Fatura mensal | GET /api/faturas; GET /api/faturas/{id} |
| Detalhe do cálculo | items[].calculation + calculation da fatura |
| Perfil | GET /api/usuarios/eu; GET /api/unidades; edição de perfil não possui endpoint nesta base |

## Síndico

| Tela prevista | API pronta para uso |
|---|---|
| Dashboard | Agregar sessões, reservas, anomalias e relatório no frontend; não há indicador real de estado online |
| Carregadores | GET/POST /api/carregadores; código, modelo, potência nominal, conectores, localização e telemetria indisponível |
| Reservas | GET /api/reservas (todas); cancelamento; disponibilidade; POST /api/reservas/no-show/processar |
| Sessões | GET /api/sessoes (todas); detalhes por id |
| Anomalias | GET /api/anomalias?status=pending_review; POST /api/anomalias/{id}/revisao; GET /api/usuarios para atribuir órfã |
| Tarifas | GET/POST /api/tarifas: versões completas com preços Green/Grid, janelas, ociosidade e overhead |
| Configurações | GET/POST /api/impostos; GET/POST /api/unidades; demais parâmetros dependem de escopo futuro |
| Financeiro | POST /api/faturas/gerar; GET /api/faturas; POST /api/faturas/{id}/fechar; GET /api/relatorios/arrecadacao |

## Contratos importantes

- `role`: resident ou manager. Não interpretar nomes exibidos na interface para determinar permissão.
- Reserva: active, in_use, completed, cancelled, no_show.
- Sessão: end_status separado de validation_status (pending, approved, suspended, rejected). “Aprovada” não equivale a “paga”.
- Fatura: open ou closed. Fechada não aceita recalcular. Pagamentos não estão no MVP.
- Anomalia: pending_review, approved, rejected. A decisão manda approve/reject. Aprovar órfã exige user_id; sessão com reserva mantém o dono daquela reserva.
- Datas HTTP: ISO 8601 com offset. Apresentar no fuso do condomínio. Não enviar datetime-local sem conversão explícita.
- Valores monetários e kWh retornados como strings; formatação BRL na apresentação. Não recalcular o total para substituir o backend.
- `id` da sessão é inteiro interno; `external_id` é o identificador vindo da fonte. Não misturar com session_id da ingestão.
- `VITE_API_BASE_URL` contém somente a origem do backend, sem /api. Vazio usa a mesma origem e o proxy.
- Código de disponibilidade não expõe id/nome de outro morador. POST de reserva continua sujeito a 409 mesmo após consultar a agenda.

## Cliente e autenticação

`src/api/schema.d.ts` é gerado, não editar à mão. `createApiClient()` oferece GET/POST tipados pelo contrato; `unwrap()` lança ApiError com status e detail da resposta. `AuthProvider.login()` recebe token, consulta o perfil e guarda o token em memória. 401 limpa o contexto. Recarregar a página exige novo login; persistência/renovação de sessão deve ser uma decisão explícita da próxima etapa.

```tsx
const { api } = useAuth();
const reservations = unwrap(await api.GET('/api/reservas'));
```

Sem senha, JWT_SECRET ou acesso direto ao PostgreSQL no frontend. A navegação por perfil complementa a autorização real da API. O formulário de login está implementado e preserva a autenticação em memória.

## Estados e IHC das telas

Cada consulta precisa de carregando, vazio, erro, sucesso e opção de tentar novamente. Para escrita, prevenir cliques repetidos e confirmar sucesso pelo retorno da API. Tratar especialmente 401 (autenticação), 403 (permissão/bloqueio), 404 (registro indisponível), 409 (conflito) e 422 (campos inválidos).

O morador precisa entender o total e o motivo de cada parcela. O síndico precisa distinguir dados inválidos, sessões órfãs e suspeitas estatísticas. Exibir descrição dos motivos, critérios do cálculo e as premissas do baseline. Evitar dizer que a sessão veio do equipamento quando source=simulator.

PWA: manifest, ícones PNG 192/512 e maskable e worker de contingência incluídos. O service worker só registra em build de produção e guarda apenas uma página offline. Não armazenar tokens, sessões ou faturas em cache. Instalação nos dispositivos-alvo não foi comprovada; consultas e ações dependem da API.

Sequência implementada nas quatro entregas: login/perfil → reserva e agenda → sessões → fatura e memória → revisão de anomalias → consulta de parâmetros → financeiro/recomendação. A rejeição de anomalia simulada pela interface foi persistida em 12/10; aprovação e atribuição órfã pela interface continuam sem comprovação. Conservar acessibilidade semântica, foco, erros associados aos campos e funcionamento em telas estreitas.
