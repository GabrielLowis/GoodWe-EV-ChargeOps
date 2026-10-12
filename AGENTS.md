# EV ChargeOps — contexto para continuar

Leia README.md, docs/INTEGRATION.md e docs/FRONTEND.md antes de alterar o projeto.

- Leia também docs/ENTREGAS-FRENTE5.md: é o plano atual e prevalece sobre o escopo amplo em docs/PLANEJAMENTO-FRENTE5.md e listas de funcionalidades dos outros documentos.
- Estado funcional em 12/10/2026: frontend das entregas 1–4 implementado; rejeição de anomalia simulada persistida pela interface. Aprovação/atribuição órfã pela interface e instalação PWA em aparelho não comprovadas. Consulte frontend/RESOLUCAO-OVERVIEW.md e docs/VALIDACAO-ENTREGA.md; execute somente o escopo autorizado pelo usuário.
- Planejamento: quatro entregas de aproximadamente duas horas, oito horas totais, prazo acadêmico em 13/10/2026. Priorize os fluxos funcionais do pacote principal; cadastros administrativos complexos e acabamento detalhado são extras.
- Desenvolva somente o frontend. Não altere backend, migrations, schema, IA ou infraestrutura para viabilizar uma tela sem aprovação específica do usuário. Informe a incompatibilidade concreta e continue as partes independentes.
- Ações pela API existente (reservar, revisar, gerar/fechar faturas) fazem parte do frontend e podem persistir registros normalmente. Não confunda isso com autorização para mudar o código do backend ou a estrutura do banco.
- Não amplie o trabalho com segurança adicional, escala ou preparação para produção. Preserve o login/perfis existentes, os contratos e o funcionamento da base.
- Fonte de verdade do banco: backend/migrations + backend/db/models.py (Frente 3). Não use create_all nem o schema legado da Frente 2.
- API integrada: backend/api + backend/main.py. Prefixo /api. Auth e permissões consultam o papel do usuário no banco.
- Cobrança: backend/rateio e backend/faturamento. Use Decimal; não faça cálculos financeiros no frontend.
- IA: condocharge_ai. Modelo reconstituído do CSV no ambiente atual; resultado ML não é probabilidade calibrada.
- Telemetria real GoodWe/SEMS/Modbus não foi conectada. O simulador usa source=simulator e não prova integração física.
- Preserve deliveries/ como referência das entregas recebidas. Alterações ficam nos módulos ativos.
- Após mudar schemas/rotas, execute python -m scripts.export_openapi e npm --prefix frontend run api:generate.
- Datas HTTP incluem offset. Valores Decimal saem em strings; timestamps e ids têm contratos distintos dos pacotes originais.
- Testes de banco usam apenas TEST_DATABASE_URL com nome terminado em _test. Nunca aponte a suíte ao banco de desenvolvimento/produção.
- Não publique, envie commits ou altere infraestrutura externa sem instrução do usuário. Não introduza dados fictícios como evidência real.
