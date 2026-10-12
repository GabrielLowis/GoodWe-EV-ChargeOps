# Identidade visual GoodWe — análise para EV ChargeOps

**Pesquisa:** 12/10/2026. **Contexto:** hackathon GoodWe × FIAP. **Entrega:** análise e planejamento; a interface existente não foi alterada.

A direção recomendada é uma interface clara, técnica e sóbria: **vermelho GoodWe nos pontos de ação e identificação, branco nas superfícies, grafite nos textos e áreas de apresentação, e Montserrat na tipografia**. O vínculo com a GoodWe deve aparecer na marca e nos detalhes recorrentes, sem reorganizar os fluxos do produto.

## 1. Método e grau de certeza

Foram consultados o site brasileiro, a página de produtos, a página HCA G2, o anúncio oficial de renovação da marca e a central de materiais de divulgação. No navegador, foram inspecionados estilos computados, imagens e regras CSS. O SVG utilizado no cabeçalho brasileiro foi preservado como referência em [goodwe-logo-site.svg](design-goodwe/referencias/goodwe-logo-site.svg).

No projeto foram lidos README, AGENTS, INTEGRATION, FRONTEND, ENTREGAS-FRENTE5 e VALIDACAO-FINAL, além de estilos, componentes compartilhados, navegação e arquivos PWA. O login em `http://127.0.0.1:5173/` foi observado no navegador; as demais telas foram analisadas pelo código e pela documentação existente. Não foi realizado um novo percurso autenticado nem uma nova validação funcional.

Três categorias evitam transformar interpretação em norma oficial:

| Categoria | Significado |
|---|---|
| Observado | Presente nos materiais oficiais ou no frontend atual |
| Interpretação | Leitura de design a partir desses materiais |
| Proposta | Decisão sugerida especificamente para o EV ChargeOps |

**Não foi obtido um manual normativo completo de identidade nem um kit específico do hackathon.** HEX observado no SVG/CSS é evidência digital, não especificação Pantone/CMYK. Pesos, margens de proteção, tamanhos mínimos e tokens propostos abaixo não são normas oficiais da GoodWe. A fonte da interface também não identifica, por si só, a fonte usada para desenhar o logotipo.

Os registros técnicos e cálculos de contraste estão em [evidencias.json](design-goodwe/evidencias.json). O [plano de aplicação](DESIGN-GOODWE-PLANO.md) define o escopo por arquivo.

## 2. Marca e logotipo

### O que foi observado

O cabeçalho brasileiro usa um logotipo horizontal vetorial, de letras geométricas personalizadas, predominantemente vermelho. Seu SVG declara `fill:#E60012` e `viewBox="0 0 767.4 114"`, proporção aproximada de **6,73:1**. [SVG oficial utilizado pelo site](https://br.goodwe.com/Public/Uploads/uploadfile/images/20220325/logo3.svg).

O anúncio de renovação publicado em 10/01/2022 descreve uma marca mais simples e plana, com ênfase no elemento VV, ligação e colaboração, mantendo o vermelho. Isso sustenta uma direção tecnológica e de energia compartilhada para o projeto. [Anúncio oficial, em chinês](https://www.goodwe.com/news-exhibition/news/4297.html).

### Como aplicar ao projeto

- Manter **EV ChargeOps** como nome do produto e o contexto **GoodWe × FIAP · Projeto acadêmico**.
- Exibir o SVG GoodWe como assinatura visual separada do nome do produto, em uma faixa branca ou superfície clara do login e do cabeçalho/menu.
- Preservar a proporção usando largura definida e altura automática. Uma largura de 128–144 px resulta em aproximadamente 19–21 px de altura; conferir a leitura no contexto real.
- Usar um espaçamento inicial de 12–16 px em relação a textos e bordas. É proposta de layout, não margem oficial de proteção.
- Não digitar “GOODWE” em Montserrat para reproduzir a marca; não esticar, recortar o VV, aplicar sombra, contorno ou filtro para fabricar uma variante.
- Se for necessária uma versão branca, usar um arquivo oficial correspondente. A solução inicial funciona com o SVG vermelho em superfície branca.
- A FIAP pode continuar identificada por texto. Um logo FIAP só deve entrar a partir de material oficial, sem criar uma composição que pareça uma nova marca conjunta.

O ícone de instalação do **EV ChargeOps** deve continuar identificando o aplicativo acadêmico. A proposta é adaptar o raio existente para grafite/vermelho/branco, em vez de reduzir o logotipo horizontal GoodWe a um ícone ilegível.

## 3. Cores e distribuição

### Paleta observada

| Cor | Evidência | Papel visual observado |
|---|---|---|
| `#E60012` | SVG da marca e CSS | Vermelho recorrente da identidade e dos destaques |
| `#FF7759` | Gradiente computado de chamadas do site | Extremidade coral de um gradiente para vermelho |
| `#FFFFFF` | Superfícies e títulos sobre imagens | Base clara e contraste |
| `#333333` | Texto/títulos computados | Grafite de leitura |
| `#666666` | Descrições computadas | Texto secundário |
| `#13212E` | Links de navegação computados | Tom escuro usado na navegação |

As famílias tipográficas e o gradiente são verificáveis no [CSS público](https://br.goodwe.com/Public/Pt/css/main.css). O site também usa fotografias com cores próprias, que não devem ser confundidas com uma paleta institucional fechada.

### Paleta proposta para o EV ChargeOps

| Token sugerido | Valor | Aplicação |
|---|---|---|
| `--brand` | `#E60012` | Botões principais sólidos, detalhes e ícones de destaque |
| `--brand-hover` | `#B8000E` | Hover, links pequenos e texto da navegação selecionada |
| `--brand-soft` | `#FFF1F2` | Fundo do item de menu ativo e pequenos destaques |
| `--accent-coral` | `#FF7759` | Detalhe decorativo restrito; não base de botão com texto branco |
| `--text` | `#333333` | Títulos, conteúdo e números financeiros |
| `--muted` | `#666666` | Descrições, metadados e rótulos secundários |
| `--canvas` | `#F6F6F6` | Fundo geral neutro |
| `--surface` | `#FFFFFF` | Cards, formulários e sidebar |
| `--border` | `#DDDDDD` | Separadores decorativos e bordas de cards |
| `--control-border` | `#737373` | Contorno dos campos quando necessário para identificar o controle |
| `--hero` | `#262626` | Base do painel ilustrado de login e do banner inicial |

Os tokens de adaptação, incluindo hover, fundo suave e contorno, são propostas. Não atribuir todos à paleta oficial. Distribuição sugerida: predominância de branco/cinza claro, grafite na leitura e vermelho como acento. Evitar uma aplicação inteiramente vermelha ou números de fatura vermelhos por padrão, o que pode parecer erro ou débito vencido.

### Cores funcionais

| Informação | Texto/fundo propostos | Critério |
|---|---|---|
| Sucesso/aprovada | `#166534` / `#F0FDF4` | Verde limitado a resultado positivo, com label preservado |
| Pendente/atenção | `#92400E` / `#FFFBEB` | Âmbar, mantendo o texto do estado |
| Rejeitada/erro | `#991B1B` / `#FEF2F2` | Vermelho escuro de erro, separado do botão principal pela apresentação |
| Em uso/informação | `#1E40AF` / `#EFF6FF` | Azul de informação |
| Encerrada/cancelada/neutra | `#666666` / `#F6F6F6` | Cinza, sem reinterpretar o significado do status |

O verde sai da identidade geral; pode permanecer na semântica de sucesso ou no contexto explícito de energia Green. Nunca mudar os estados ou a distinção entre encerramento, aprovação e cobrança apenas para ajustar cores.

### Contraste calculado

Os valores abaixo usam luminância relativa sRGB. Para texto comum, a referência é 4,5:1; para texto grande, 3:1. [W3C — contraste mínimo](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html).

| Combinação | Razão aproximada | Decisão |
|---|---:|---|
| Branco sobre vermelho `#E60012` | 4,80:1 | Adequado para o botão principal sólido |
| Branco sobre coral `#FF7759` | 2,61:1 | Evitar texto branco sobre a extremidade coral |
| Grafite `#333333` sobre branco | 12,63:1 | Adequado para leitura |
| Cinza `#666666` sobre `#F6F6F6` | 5,31:1 | Adequado para texto secundário |
| Vermelho `#E60012` sobre rosa `#FFF1F2` | 4,37:1 | Usar o vermelho escuro proposto no texto pequeno do menu |
| Branco sobre grafite `#262626` | 15,13:1 | Adequado na base sólida do painel de apresentação |

Esses cálculos validam pares sólidos, não o contraste de textos sobre uma fotografia ainda não escolhida. No login, o texto deve ficar em uma área de grafite sólido ou overlay forte; conferir depois a composição renderizada.

## 4. Tipografia

**Observado:** o site brasileiro declara `MontserratRegular`, `MontserratLight` e `MontserratBold`. Corpo/navegação usam Regular; títulos de seções e do HCA G2 usam Bold; descrições usam Light em diferentes partes. Essas declarações foram verificadas no CSS e em estilos computados, não inferidas apenas pela aparência. [CSS oficial](https://br.goodwe.com/Public/Pt/css/main.css), [página HCA G2](https://br.goodwe.com/carregadores-hca-g2-goodwe).

**Proposta:** uma família Montserrat para toda a interface, com pesos 400, 500, 600 e 700. Usar 400 nos textos operacionais em vez de imitar os pesos muito leves de peças promocionais. Montserrat pode ser obtida de sua distribuição no [repositório Google Fonts](https://github.com/google/fonts/tree/main/ofl/montserrat); na implementação, empacotar arquivos locais e manter a licença da distribuição.

| Elemento | Proposta |
|---|---|
| Título de página | 30–40 px desktop, 28–32 px mobile, peso 700, altura 1,15–1,25 |
| Título de card | 18–20 px, peso 600 |
| Corpo | 15–16 px, peso 400, altura 1,5–1,65 |
| Labels/botões | 14–15 px, peso 500/600 |
| Metadados | 12–14 px, sem encolher textos necessários à decisão |
| Chamadas curtas em caixa alta | Uso pontual, com espaçamento moderado |
| Valores/horários | Números tabulares quando disponíveis; preservar formatação e casas decimais |

A troca de fonte altera a largura das frases. Revisar menu mobile, mostrar/ocultar senha, datas e títulos antes de ajustar dimensões. Reduzir o tracking negativo atual: partir de aproximadamente `-0.02em` nos títulos, conservando o layout. Fontes locais com `font-display: swap` e fallback `Segoe UI, system-ui, sans-serif`; a página offline pode usar o fallback, pois o worker não armazena a fonte.

## 5. Ícones e elementos gráficos

O site oficial mistura ícones de categorias energéticas e símbolos de interface. Não foi identificada uma biblioteca única como norma corporativa. A proposta para o aplicativo é manter os SVGs locais com `currentColor`, grade de 24 × 24, traço aproximadamente 1,75–2 px e uma linguagem uniforme, sem acrescentar uma dependência para essa troca.

| Função | Ícone sugerido |
|---|---|
| Início/visão geral | Casa ou painel, conforme o label existente |
| Nova reserva | Calendário com adição |
| Reservas/agenda | Calendário |
| Recargas/sessões | Plugue/carregador |
| Faturas/financeiro | Documento com valor ou recibo |
| Sugestão de horário | Relógio com energia/sol |
| Anomalias | Triângulo de atenção |
| Cadastros e parâmetros | Ajustes/deslizadores |
| Saída | Porta com seta |

Hoje financeiro e faturas usam `home`, anomalias usam `bolt` e parâmetros usam `plug`. Isso torna funções diferentes visualmente semelhantes. A mudança é só da figura: manter labels, links, ordem e ações. Ícones decorativos seguem `aria-hidden`; não transformar botões com texto em botões sem label.

## 6. Fotografia, fundos e acabamento

**Observado:** a página de produtos apresenta equipamentos claros/escuros em ambiente neutro. O HCA G2 aparece sobre fundo ambiental desfocado, com superfícies translúcidas, títulos brancos e acentos vermelhos. A mídia inicial dessa página não reproduziu no navegador consultado; o produto estático e demais imagens ficaram disponíveis. [Produtos](https://br.goodwe.com/products?tp=8), [HCA G2](https://br.goodwe.com/carregadores-hca-g2-goodwe).

**Interpretação:** tecnologia concreta, equipamentos e uso cotidiano são referências mais pertinentes que uma decoração verde genérica.

**Proposta preferencial para o login:** conservar as duas colunas, a frase e o formulário. Usar grafite no painel esquerdo, um detalhe vermelho e uma imagem estática do carregador, concentrada no espaço hoje ocupado pela ilustração CSS. Caso seja usada fotografia de instalação/garagem, aplicar apenas ao painel narrativo, com o texto em área protegida. O formulário permanece em superfície branca.

Referências de imagem observadas, para seleção na futura implementação:

| Referência | Origem | Uso possível |
|---|---|---|
| Produto HCA G2 isolado | [Arquivo mostrado na página](https://br.goodwe.com/Public/Uploads/uploadfile7/images/20250325/et50(7).png) | Substituir a ilustração no login, após conferir recorte e transparência |
| Composição HCA G2 | [Imagem da página](https://br.goodwe.com/Public/Uploads/uploadfile7/images/20250307/EVChargerG2-2.png) | Referência de composição; verificar se contém textos antes de reutilizar como fundo |
| Foto de instalação solar/carport | [Case oficial brasileiro](https://br.goodwe.com/Public/Uploads/uploadfile7/files/20230725/GOODWE-CASESUCESSO-PARQUEAQUATICOSOLARIS.pdf) | Referência secundária de ambiente; não prova instalação no condomínio |

Nenhuma fotografia foi incorporada ao frontend nem escolhida definitivamente. Evitar campanhas com datas, banners com texto embutido e fotos de instalações apresentadas como sendo do projeto. A imagem ilustra o contexto; não comprova conexão física. Material do evento deve prevalecer se trouxer orientações específicas.

No mobile, conservar o painel compacto e ocultar a imagem grande, como a ilustração atual. Na home, o banner pode usar grafite e um detalhe/recorte leve, sem foto sob valores ou botões. Reservas, faturas, anomalias e parâmetros permanecem sobre fundo neutro. Sem carrossel, vídeo, animação nova, painel de marketing ou parallax.

Raios de borda sugeridos: 8–10 px em controles e 12–14 px em cards, aproveitando as dimensões existentes. Sombras discretas e neutras. A barra arredondada/translúcida do site institucional é inspiração para acabamento, não motivo para substituir a sidebar operacional.

## 7. Diagnóstico do frontend atual

| Área | Situação atual comprovada pelo código | Mudança proposta |
|---|---|---|
| Base | Segoe UI, texto `#253A35`, fundo `#F5F7F6`, `--green:#174C40` | Montserrat, grafite, fundo neutro e tokens de marca |
| Login | Painel `#164A3F`, ilustração CSS verde, formulário claro | Painel grafite, assinatura GoodWe, vermelho e imagem opcional |
| Marca compartilhada | Raio em bloco verde e GoodWe escrita em texto pequeno | Nome do produto preservado com assinatura SVG GoodWe |
| Botões e links | Verde estrutural e estados de hover esverdeados | Vermelho sólido no principal, secundários neutros |
| Navegação | Seleção `#EAF3ED` / `#1B5743` | Seleção rosa suave/vermelho escuro e indicação além da cor |
| Home | Banner verde e destaques esverdeados | Banner grafite, acentos vermelhos, cards brancos |
| Métricas/faturas | Números e totais usam `--green` | Números grafite; vermelho limitado à ação/destaque |
| Estados | Verde/âmbar/azul/vermelho para situações distintas | Preservar a semântica e centralizar as cores de status |
| Ícones | Sete desenhos reutilizados para muitas funções | Novos desenhos locais específicos, mesmo componente |
| PWA/offline | Theme-color, SVG e PNGs verdes; CSS offline próprio | Harmonizar cores e ícone do aplicativo; manter funcionamento |

Existe uma referência a `var(--text)` no textarea, mas o token não está definido na raiz atual. O pacote de tokens proposto deve definir esse nome sem alterar o formulário de revisão.

## 8. Direção escolhida e limites

**Direção escolhida:** “EV ChargeOps com identidade GoodWe”: interface operacional clara, títulos Montserrat, grafite na apresentação, vermelho na ação e marca oficial como assinatura. É suficiente para remeter ao patrocinador e mantém reconhecíveis os fluxos do morador e síndico.

Alternativa simplificada, se a seleção de imagem consumir o tempo disponível: aplicar a mesma paleta/fonte e recolorir a ilustração CSS atual em cinza/branco/vermelho. O resultado ainda deve ficar coerente; imagem não é requisito para concluir o pacote visual.

O plano não inclui mudança de API, autenticação, permissões, roteamento, consultas, cálculos, dados, regras, telas ou infraestrutura. Não foram rodados build/testes nesta etapa documental. A evidência funcional de 11/10 continua sendo histórica e não prova um redesign, que ainda não foi implementado.
