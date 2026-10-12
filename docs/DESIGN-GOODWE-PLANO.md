# Plano de aplicação visual GoodWe — frontend EV ChargeOps

**Data:** 12/10/2026. **Estado:** pronto para implementação posterior; nenhuma mudança de interface executada. **Base:** [relatório de identidade visual](DESIGN-GOODWE-RELATORIO.md).

## 1. Resultado esperado

O mesmo aplicativo, com os mesmos fluxos e conteúdo, passa a remeter à GoodWe por meio de Montserrat, vermelho `#E60012`, branco/grafite, assinatura oficial e ícones mais claros. A adaptação cobre login, navegação, telas dos dois perfis e superfícies PWA. A imagem de login é opcional e não deve impedir a conclusão antes da apresentação acadêmica de 13/10.

Este documento orienta somente o trabalho visual adicional pedido pelo usuário. Não reabre as entregas funcionais 1–4 de [ENTREGAS-FRENTE5](ENTREGAS-FRENTE5.md) e não expande seu escopo.

## 2. Fronteira entre aparência e comportamento

| Permitido na implementação visual | Preservar integralmente |
|---|---|
| Cores, fontes, pesos, bordas, sombras, espaçamento pontual | Hooks, consultas, mutações e payloads |
| SVGs decorativos e mapeamento visual de ícones | Rotas hash, destinos, labels operacionais e ordem dos menus |
| SVG oficial em componente de marca | Login, alternância de senha, perfis, logout e foco de navegação |
| Imagem decorativa local no painel de login | Campos, validações, required/disabled, confirmação e mensagens |
| Ajustes pequenos para acomodar a nova fonte em mobile | Dados, agregações, seleção de período e cálculos/formatação |
| Cor do navegador, manifest e ícones PWA | URLs, scope, start_url, instalação, registro e política do worker |
| Aparência da página offline | Mensagem e ação de reconexão; APIs continuam dependentes da rede |

Não refatorar componentes de domínio, criar novas telas, adicionar gráficos, mudar regras ou aumentar a cobertura de funcionalidades. Não instalar bibliotecas de UI/ícones para executar esta adaptação. Arquivos de backend, migrations, IA, dados, deliveries e infraestrutura ficam fora.

## 3. Mapa de arquivos

| Arquivo/grupo | Alteração visual prevista | Limite |
|---|---|---|
| `frontend/src/styles.css` | Tokens; fonte; cores de todos os componentes; foco e ajustes de leitura | Manter os grids e breakpoints de 1100/1000/760 px; ajustar apenas problemas provocados pela fonte |
| `frontend/src/components/ui.tsx` | Assinatura no `Brand`; acrescentar paths em `Icon` | Preservar `Alert`, `QueryError`, props existentes e semântica |
| `frontend/src/App.tsx` | Trocar apenas nomes dos ícones de navegação | Não alterar lógica de seleção, handlers, routes, perfis ou links |
| `frontend/src/pages/LoginPage.tsx` | Imagem/markup decorativo no painel esquerdo, se utilizada | Não editar state, submit, auth, inputs ou botão Mostrar/Ocultar senha |
| `frontend/src/pages/HomePage.tsx` | Somente ícone decorativo, se CSS não bastar | Manter consultas, dados, atalhos e callbacks |
| Demais `frontend/src/pages/*.tsx` | Preferir alteração via estilos compartilhados; ícones apenas onde necessário | Não reescrever páginas nem inserir novos dados/indicadores |
| `frontend/src/assets/brand/` | Novo SVG GoodWe de origem oficial | Preservar desenho, proporção e proveniência |
| `frontend/src/assets/fonts/` | Montserrat local e licença da distribuição escolhida | Sem dependência remota obrigatória ou novo cache offline |
| `frontend/src/assets/images/` | Uma imagem estática de login, se escolhida | Sem campanhas, vídeo, carrossel ou informações inventadas |
| `frontend/index.html` | Apenas `theme-color` para grafite | Manter URLs, título do produto e ponto de entrada |
| `frontend/public/manifest.webmanifest` | `theme_color:#262626`, `background_color:#F6F6F6` | Manter identidade do app, tamanhos/purpose, URLs e modo |
| `frontend/public/icon.svg` e PNGs 192/512/maskable | Recolorir o ícone próprio do app, derivar PNGs coerentes | Não substituir por logotipo horizontal espremido; conferir área segura maskable |
| `frontend/public/offline.html` | Paleta, tipografia de fallback e SVG coerentes | Preservar conteúdo e link Tentar novamente |
| `frontend/public/sw.js`, `src/main.tsx`, auth/api/hooks/utils | Nenhuma alteração prevista | Política de cache e comportamento preservados |

Se o navegador mantiver a antiga página offline em cache, conferir o novo build com um perfil/contexto de teste limpo. Isso não autoriza ampliar o cache, armazenar fontes/dados ou reescrever o worker.

## 4. Pacote A — base visual e componentes compartilhados

**Estimativa:** 45–60 minutos; depende do ajuste tipográfico real, não é garantia.

1. Registrar hashes dos arquivos ativos e inventariar as alterações preexistentes. O repositório atualmente apresenta arquivos não rastreados; `git diff` sozinho não demonstra preservação.
2. Preparar Montserrat local com pesos 400/500/600/700, `font-display:swap` e fallback. Usar uma distribuição oficial aberta com sua licença, sem copiar indiscriminadamente a pasta de fontes do site.
3. Criar tokens conforme o relatório: marca, hover, fundo suave, texto, muted, superfícies, bordas, controles e estados funcionais.
4. Migrar `--green` para papéis visuais explícitos. Mapear cada uso: botão principal recebe vermelho; número de fatura recebe grafite; mensagem de sucesso continua com a cor funcional adequada. Não fazer substituição global de todos os verdes por vermelho.
5. Remover tons verdes estruturais hardcoded em login, sidebar, topbar, avatar, tags neutras, cards de métricas, atalhos, detalhes, confirmações financeiras e rodapé.
6. Aplicar Montserrat aos controles, incluindo textarea. Retocar títulos, labels e espaços apenas quando a nova fonte causar quebra/encavalamento.
7. Preservar foco evidente: anel externo escuro e separação clara para funcionar sobre botão vermelho, card branco e painel grafite. Conferir com teclado.

**Aparência ao terminar:** todas as telas já compartilham uma identidade vermelho/branco/grafite, sem depender de uma fotografia.

## 5. Pacote B — assinatura, ícones e apresentação

**Estimativa:** 30–45 minutos. Imagem é uma opção com tempo limitado.

1. Conferir o SVG de referência e preparar seu uso no componente `Brand`. Nome do produto e indicação acadêmica permanecem legíveis. Logo vermelho fica sobre superfície branca/clara; não fabricar uma versão branca por CSS.
2. Acrescentar os ícones de recibo/documento, ajustes, atenção, calendário com adição e relógio/energia. Reutilizar `Icon`, dimensões atuais, `currentColor` e `aria-hidden`.
3. Trocar o desenho de financeiro/faturas, parâmetros, anomalias, sugestão e nova reserva. Conservar labels e destinos existentes.
4. No login, preservar as duas colunas e o texto. Painel esquerdo grafite, assinatura GoodWe e acento vermelho. Formulário permanece claro e no mesmo percurso de teclado.
5. Se a imagem HCA G2 funcionar no espaço existente, utilizá-la como ilustração decorativa com dimensões reservadas, arquivo local e `object-fit:contain`. Conferir qualidade/recorte/transparência antes de decidir.
6. Se a opção for uma fotografia de ambiente, manter texto sobre uma zona protegida por grafite e usar recorte desktop/mobile. Escolher somente uma imagem sem datas, slogans ou textos de campanha incorporados.
7. Limitar a preparação de imagem a cerca de 15 minutos. Se o material não estiver adequado, recolorir a ilustração CSS existente e concluir o pacote. Sem gerar novas imagens por padrão.
8. Recolorir o banner inicial do morador para grafite com acento vermelho. Não criar uma hero no dashboard do síndico que desloque seus indicadores.

**Regra para imagens:** ilustrativas, sem sugerir que são equipamentos do condomínio ou integração física comprovada. Usar arquivos locais após verificar a origem e a adequação ao evento; não depender de hotlink no site GoodWe.

## 6. Pacote C — PWA e coerência das superfícies

**Estimativa:** 15–25 minutos.

1. Harmonizar `theme-color` do HTML com `theme_color` do manifest em grafite e neutralizar `background_color`.
2. Recolorir o ícone do aplicativo: fundo grafite, raio branco e eventual detalhe vermelho. Gerar as variantes 192, 512 e maskable a partir do mesmo desenho.
3. Preservar a área segura do ícone maskable e conferir recortes circulares/quadrados. O logotipo GoodWe horizontal permanece como assinatura dentro do produto.
4. Aplicar a mesma direção à página offline, com fonte de sistema como fallback garantido. Não adicionar fontes/contas/dados à política de cache.

Esse pacote trata aparência. Não constitui comprovação de instalação em aparelho físico e não exige alterar o funcionamento PWA.

## 7. Aplicação por tela

| Superfície | Resultado visual | O que não muda |
|---|---|---|
| Login | Grafite + marca oficial + ação vermelha + Montserrat; imagem opcional | E-mail/senha, mensagens, Mostrar/Ocultar, submit e perfil |
| Sidebar/topbar | Branco/cinza, seleção rosa suave/vermelho escuro, ícones específicos | Ordem, links, navegação, conta e logout |
| Início do morador | Banner grafite e cards claros; números neutros | Consultas, reservas, sessões, faturas e atalhos |
| Nova reserva/lista/agenda | Campos legíveis, ação principal vermelha, disponibilidade neutra | Datas, disponibilidade, conflito, reserva e cancelamento |
| Sugestão | Mesma hierarquia visual; premissas com boa leitura | Baseline, valores retornados e transporte ao formulário |
| Recargas/sessões/detalhe | Métricas neutras e badges semânticos | Green/Grid, origem simulator, término versus validação |
| Faturas/detalhe/financeiro | Números grafite, ações hierarquizadas, memória legível | Valores, parcelas, datas, período, cálculo e confirmação |
| Anomalias/detalhe | Ícone de atenção e estados distintos | Filtros, motivos, revisão, atribuição e observações |
| Parâmetros | Cards/branco/cinza e ícone de ajustes | Conteúdo consultivo e contratos existentes |
| Offline/navegador/ícone | Mesma paleta do aplicativo | Limitação offline e URLs |

## 8. Verificação proporcional ao escopo

**Estimativa:** 25–40 minutos. Reservar esse tempo antes da apresentação.

### Integridade do comportamento

- Comparar os arquivos alterados com o registro inicial e revisar mudanças em TSX: somente apresentação, SVGs e nomes de ícone; nenhum handler, consulta, parâmetro, dado ou regra alterado.
- Rodar `npm --prefix frontend run build` e `npm --prefix frontend test` uma vez após concluir a adaptação. São verificações futuras; não executadas para este relatório.
- Não criar uma suíte nova que apenas reproduza CSS. Ajustar teste existente somente se uma mudança visual autorizada exigir, preservando asserções de comportamento e nomes acessíveis.
- Não rodar testes de banco, migrations, seeds ou simulador para validar o design.

### Navegador e leitura

- Conferir desktop em 1280 px e mobile em 390 px; usar 320 px para confirmar que fonte/marca não quebram menu e login. Revisar especialmente as regiões que usam breakpoints existentes.
- Percorrer login, menus e consultas dos dois perfis com dados já existentes. Validar mostrar/ocultar senha, detalhe de sessão, fatura/memória e página de parâmetros.
- Checar tamanhos, overflow, quebra de nomes/datas, labels, foco visível, contraste e distinção entre principal/secundário/destrutivo.
- Conferir o build preview, URLs de SVG/PNG/fontes e contingência offline em contexto limpo. Registrar limites; não declarar instalação em aparelho.
- Conferir carregando, vazio, erro, sucesso e disabled quando disponíveis; usar renderização controlada local se necessário para aparência, identificando-a como evidência visual controlada.
- Não criar/cancelar reservas, revisar ocorrências, gerar/recalcular/fechar faturas apenas para testar cores. Os testes existentes cobrem lógica; a inspeção manual pode limitar-se a consultas e estados locais.

Guardar screenshots representativas e um registro curto de arquivos/validação após a implementação. As evidências anteriores permanecem como histórico, sem sobrescrever `VALIDACAO-FINAL` para alegar uma execução que não ocorreu.

## 9. Critérios de aceite

- [ ] Identidade geral em vermelho/branco/grafite; verde restrito a significado funcional explícito.
- [ ] Logo GoodWe oficial legível e sem distorção; EV ChargeOps e contexto acadêmico preservados.
- [ ] Montserrat integrada com fallback; textos e controles legíveis em desktop e mobile.
- [ ] Ícones distinguem financeiro, parâmetros, anomalias e recarga, sem trocar ações ou labels.
- [ ] Imagem opcional contribui para o contexto e não compromete formulário/contraste; ausência dela não impede aceite.
- [ ] Login, menus, detalhes, memória financeira e estados continuam utilizáveis por teclado.
- [ ] Ícone, manifest, cor do navegador e página offline coerentes, mantendo a política PWA.
- [ ] Build e testes existentes aprovados; inspeção visual documentada com seus limites.
- [ ] Comparação dos arquivos confirma preservação dos contratos e da lógica; nenhuma alteração fora do frontend autorizado.

## 10. Ordem, tempo e regra de encerramento

Executar **A → B → C → verificação**, em um pacote único de adaptação. Estimativa total: **aproximadamente 2–3 horas**, adicional às entregas funcionais; priorizar a validação se houver menos tempo. Cortar primeiro fotografia e detalhes decorativos, preservando fonte, cores, assinatura, ícones e funcionalidade.

Depois da verificação, permitir uma rodada curta de correções para problemas concretos de leitura, contraste ou overflow. Não reabrir escolhas já satisfeitas por preferência estética secundária e não refazer a arquitetura/layout geral. Se surgir incompatibilidade funcional preexistente, registrar separadamente; este plano visual não autoriza corrigi-la fora do escopo.

**Conclusão desta etapa:** relatório e plano preparados. A implementação do design ainda não começou; nenhum commit ou publicação foi realizado.
