# Design GoodWe — implementação e validação

**Conferência:** 12/10/2026. **Resultado:** identidade visual aplicada ao frontend existente, conforme o plano aprovado. Sem commits ou publicação.

## O que mudou

- Paleta centralizada em vermelho `#E60012`, hover `#B8000E`, branco, cinza neutro e grafite. Valores financeiros permanecem neutros; verde/âmbar/azul/vermelho escuro conservam o significado dos estados.
- Montserrat variável local, com faixa de pesos 400–700, fallback de sistema e `font-display: swap`. Nenhuma dependência de fonte remota no aplicativo.
- SVG oficial GoodWe como assinatura de 128 px sobre superfície branca, mantendo EV ChargeOps e GoodWe × FIAP. A cópia é idêntica ao arquivo de referência.
- Ícones locais específicos para faturas/financeiro, parâmetros, anomalias, nova reserva e sugestão. Labels, links e ações preservados.
- Painel grafite no login e imagem oficial HCA G2. O arquivo original permanece intacto; o recorte CSS oculta o selo promocional “NOVO”. A imagem é decorativa e fica oculta no mobile.
- Banner inicial do morador em grafite com detalhe vermelho. Formulários, métricas, listas e detalhes usam superfícies claras.
- Cor do navegador, manifest, ícone SVG, PNGs 192/512/maskable e página offline harmonizados. Registro, cache e código do worker preservados.

Uma correção visual foi necessária em 320 px: os campos de data e horário ficam em uma coluna abaixo de 380 px. Nos demais tamanhos, a composição existente permanece. A nova fonte já não provoca transbordamento nesse formulário; nenhum campo, valor, validação ou handler foi alterado.

## Build, testes e navegador

| Conferência | Resultado |
|---|---|
| Build TypeScript/Vite | Aprovado; 38 módulos transformados — [build.txt](evidence/design-goodwe/build.txt) |
| Testes existentes | **50/50 aprovados, 12/12 arquivos** — [tests.txt](evidence/design-goodwe/tests.txt) |
| Desktop e mobile | Seis telas de cada perfil em 1280, 390 e 320 px; login, detalhes e memória também conferidos |
| Teclado | Mostrar/Ocultar senha por Espaço/Enter, login, saída e expansão da memória da fatura |
| Fonte e imagens | Montserrat carregada e imagens locais disponíveis no desenvolvimento e no novo build |
| HTTP | Frontend 5173, preview 4173 e arquivos/fontes/imagem/PWA retornaram 200 — [urls-http.json](evidence/design-goodwe/urls-http.json) |
| Offline real do preview | Após visita online, somente o preview temporário 4175 foi encerrado; reload exibiu “Sem conexão” com o novo visual — [offline-checks.json](evidence/design-goodwe/offline-checks.json) |

A primeira execução restrita do Vitest falhou no acesso a arquivos temporários SSR. O mesmo comando fora desse isolamento passou, sem alterar configuração, dependências ou testes. Após o ajuste visual final, build e os 50 testes foram executados novamente e passaram.

Foram consultados agenda, sessões, fila de anomalias, financeiro e parâmetros do síndico; início, nova reserva, reservas, recargas, faturas e sugestão do morador. A ocorrência #1 foi aberta apenas para conferir o formulário, sem enviar revisão. A fatura #1 teve a memória expandida por teclado; nenhuma geração ou fechamento foi executado. Uma sugestão de horário foi consultada pela rota GET, sem criar reserva.

Os estados efetivamente disponíveis foram inspecionados, incluindo espera de consulta, formulário inicial, controle desabilitado e badges de aprovação, suspensão e rejeição. Isso não equivale a provocar todas as falhas de API nem a uma auditoria completa de acessibilidade.

Em 320 px, a medição inicial do formulário mostrou um transbordamento; a medição corrigida registra `clientWidth=305` e `scrollWidth=305` (a barra vertical ocupa o restante do viewport). [browser-checks.json](evidence/design-goodwe/browser-checks.json) mantém ambas as medições como histórico; o registro `new-reservation-corrected` e a screenshot atual documentam a correção.

## Preservação comprovada

[files-verification.json](evidence/design-goodwe/files-verification.json) compara SHA256 de **270 arquivos existentes**: 12 arquivos do frontend mudaram; nenhum arquivo dos módulos protegidos mudou. Autenticação, cliente/contrato da API, hooks, utilitários, testes, worker, configuração e dependências permanecem iguais ao início desta implementação.

Além da conferência do diff, [verification.json](evidence/design-goodwe/verification.json) confirma:

- App e HomePage diferem somente nos nomes dos ícones.
- LoginPage difere somente no import do asset e na arte decorativa.
- Alert e QueryError continuam idênticos.
- O worker permanece idêntico.
- O SVG oficial copiado permanece idêntico à referência.
- As respostas de domínio das consultas antes/depois são integralmente iguais.

[api-before.json](evidence/design-goodwe/api-before.json) e [api-after.json](evidence/design-goodwe/api-after.json) contêm saúde e consultas locais sem tokens ou senhas. Reservas, sessões, faturas/detalhes, usuários, unidades, carregador, tarifas, impostos e os três estados da fila foram comparados. A digest das respostas de domínio nos dois momentos foi `290c4789a2bde39f2decc24fd2ef67caeca7145089d4e2ed9edaa3b23bf69a4b`.

Não houve criação/cancelamento de reserva, ingestão de sessão, revisão, geração/recalculo ou fechamento de fatura. Não foram executados seeds, migrations, bootstrap, simulador ou suíte de banco. O backend, banco, IA e infraestrutura externa não foram alterados para viabilizar o design.

## Assets e origem

| Asset | Origem |
|---|---|
| Logo GoodWe | [SVG do site oficial](https://br.goodwe.com/Public/Uploads/uploadfile/images/20220325/logo3.svg) |
| HCA G2 | [PNG da página oficial do produto](https://br.goodwe.com/Public/Uploads/uploadfile7/images/20250325/et50(7).png) — 1020 × 1300, original preservado |
| Montserrat e licença OFL | [Distribuição Google Fonts](https://github.com/google/fonts/tree/main/ofl/montserrat); arquivos locais em `src/assets/fonts/` |
| Ícones do aplicativo | Mesmo desenho de raio do EV ChargeOps, recolorido para grafite/branco; variantes raster derivadas com área segura maskable |

Hashes e dimensões estão em [verification.json](evidence/design-goodwe/verification.json). Sem biblioteca de UI/ícones ou pacote npm adicional.

## Evidências visuais e execução

Foram salvas **59 screenshots** em [evidence/design-goodwe](evidence/design-goodwe/). Exemplos:

- [Login desktop](evidence/design-goodwe/01-login-desktop.jpg)
- [Login 320 px](evidence/design-goodwe/02-login-320.jpg)
- [Início do morador](evidence/design-goodwe/resident-home-1280.jpg)
- [Dashboard do síndico](evidence/design-goodwe/manager-overview-1280.jpg)
- [Reserva corrigida em 320 px](evidence/design-goodwe/resident-new-reservation-320.jpg)
- [Fatura com memória expandida](evidence/design-goodwe/resident-invoice-detail-390.jpg)
- [Formulário de revisão sem envio](evidence/design-goodwe/manager-anomaly-detail-390.jpg)
- [Contingência offline](evidence/design-goodwe/offline-390.jpg)

Desenvolvimento: `http://127.0.0.1:5173/`. Preview do novo build: `http://127.0.0.1:4173/`. API/banco e Vite de desenvolvimento foram reutilizados. O preview 4173 estava parado quando conferido e foi iniciado com o comando existente; seu processo está registrado em `.local/design-goodwe-preview4173.json`. O preview temporário 4175 foi encerrado após a prova offline.

Esta conferência comprova o visual e a contingência no navegador local. Não comprova instalação PWA em aparelho físico, telemetria GoodWe real, pagamentos ou implantação externa. Os documentos/evidências das entregas anteriores permanecem como histórico.
