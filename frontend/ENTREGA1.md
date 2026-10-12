# Entrega 1 — acesso, navegação e reservas

Implementada e conferida em 08/10/2026, conforme `docs/ENTREGAS-FRENTE5.md`.

## O que foi entregue

- Login com e-mail, senha, mensagem de erro, estado de envio e saída da conta.
- Área definida pelo `role` retornado pela API. Token permanece somente em memória; recarregar exige novo login.
- Layout compartilhado: verde escuro, superfícies claras, navegação lateral no computador e menu no topo em telas estreitas. Sem novas dependências.
- Início do morador com nome, e-mail, unidade e atalhos para agendar/consultar reservas.
- Área inicial do síndico, com perfil e indicação das funções previstas nas próximas entregas. Sem antecipar a operação ou o financeiro.
- Carregadores ativos e conectores do cadastro; datas/horários de início e fim, com duração positiva de até 12 horas.
- Disponibilidade em lista para o dia de início e conector selecionados. Consulta sem identificação dos outros moradores; confirmação continua sujeita ao conflito retornado pela API.
- Reservas próprias, situação em português e cancelamento de reservas ativas com confirmação simples.
- Estados de espera, ausência de dados, erro com repetição da consulta e sucesso confirmado pelo retorno da API. Erros locais associados aos campos.
- Datas apresentadas em `America/Sao_Paulo`; envio explícito com offset `-03:00`, correspondente ao fuso do condomínio no período acadêmico.

Implementação em `src/App.tsx`, `src/pages`, `src/components/ui.tsx`, `src/hooks/useQuery.ts`, `src/utils/presentation.ts` e `src/styles.css`. Cliente gerado, autenticação existente, pacotes e contratos preservados.

## Validação realizada

`npm --prefix frontend run build`: TypeScript e build Vite aprovados.

`npm --prefix frontend test`: os três testes existentes do cliente HTTP passaram. Não foi adicionada uma suíte abrangente nem executada a suíte de banco.

Percurso no navegador, com a API e o banco de desenvolvimento existentes:

1. Senha incorreta: mensagem de acesso inválido.
2. Conta `morador@demo.local`: início com Morador Demo e unidade A-101, consultados pela API.
3. Intervalo com término anterior ao início: recusa no formulário, com erro associado ao término.
4. Reserva #2 criada em HCA01/conector 1, em 13/10/2026 das 10h às 11h. Confirmação e registro exibidos na lista.
5. Mesma janela enviada novamente: API retornou 409; formulário exibiu conflito e atualizou a disponibilidade.
6. Reserva #2 cancelada pela rota existente. Nova consulta HTTP confirmou `status=cancelled` e `busy=[]` para o dia. A reserva anterior #1 permaneceu concluída.
7. Formulário conferido em largura de 390 px: sem transbordamento horizontal, campos e navegação utilizáveis. Também foram capturados login e área do síndico nessa largura.
8. Saída da conta: retorno ao login. Conta `sindico@demo.local`: abertura da área administrativa.
9. Recarregamento da página autenticada: retorno ao login, preservando o comportamento da base.

As imagens estão em `evidence/entrega1/`: login, criação, conflito, cancelamento e versões em largura de celular. São evidências do ambiente acadêmico local, com cadastros de demonstração. A imagem de criação é anterior ao cancelamento; o estado final da reserva #2 é cancelado.

## Como repetir

Com o ambiente local preparado, usar os comandos de `docs/DEVELOPMENT.md` (`scripts/start-local.ps1` quando os serviços estiverem parados). Não reiniciar se o ambiente já estiver em execução.

Abrir http://127.0.0.1:5173. Usar as contas de demonstração acima e a senha local definida em `DEMO_PASSWORD`, sem copiá-la para o código.

Entrar como morador → Nova reserva → escolher um horário futuro → confirmar → conferir a lista → tentar a mesma janela para mostrar o conflito → cancelar somente a reserva criada para a demonstração → sair → entrar como síndico.

## Reteste solicitado — API real do projeto

Novo percurso realizado em 08/10/2026, reutilizando os serviços locais já ativos. Frontend respondeu HTTP 200; `/api/saude` confirmou banco disponível e migration `0001_schema_inicial`.

- Login incorreto recusado; login de morador aceito e perfil/unidade carregados.
- Término anterior ao início recusado no formulário.
- Reserva #4 criada em HCA01/conector 1, em 13/10/2026 das 10h às 11h; registro exibido na lista.
- Repetição da mesma janela recusada por conflito; disponibilidade mostrou 10h–11h ocupado.
- Reserva #4 cancelada com confirmação. Consulta HTTP posterior confirmou `cancelled` e `busy=[]` no dia.
- Reserva #3 preexistente (09/10/2026, 13h–18h) preservada como `active`. Demais registros preservados.
- Saída, login como síndico e retorno ao login após recarregar conferidos.
- Build e três testes existentes repetidos com sucesso.

Evidências adicionais em `evidence/entrega1/reteste/` (criação, conflito, cancelamento e síndico). Não houve necessidade de corrigir o frontend ou alterar backend/banco para este reteste. Sem impedimento observado no percurso principal da entrega 1; os limites de cenários/dispositivos abaixo continuam aplicáveis.

## Limites e preservação

Não foi necessário alterar código do backend, schema, migrations, IA ou infraestrutura. A validação persistiu uma reserva e seu cancelamento exclusivamente pelas rotas autorizadas; sem escrita direta no banco, bootstrap ou migrations.

Sessões, faturas, recomendação e operação administrativa continuam para as entregas 2–4. Nenhuma integração física, telemetria ao vivo, instalação PWA ou publicação foi validada nesta entrega.

Os estados vazios e de erro de consulta foram implementados, mas não foi forçada uma interrupção dos serviços nem removidos cadastros para demonstrar todos eles. O cadastro disponível tem um carregador e um conector: a seleção de múltiplos carregadores/conectores usa o contrato, mas esse cenário não teve evidência prática nesta base. A conferência móvel é de viewport, não instalação ou teste em aparelho físico.

Não houve commit ou publicação. A base já estava inteiramente sem rastreamento no Git antes desta entrega; esse estado foi preservado.
