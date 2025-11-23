# Resumo das Mudanças – ELO Assistente Cidadão 2.0

## Principais Inovações

### 1. Detecção Automática de Intenção
O usuário não precisa mais escolher menus ou digitar comandos. O sistema entende o contexto:
- Perguntou de lei/deputado? -> **Modo VOTOS**.
- Perguntou de benefício/documento? -> **Modo ELO**.
- Mandou foto ou áudio? -> **Modo ORÁCULO**.

### 2. DataHub Federado
Centralização de acesso a dados públicos. Em vez de consultar apenas uma fonte, o ELO agora varre:
- Câmara e Senado (Legislativo Federal).
- Querido Diário (Atos municipais).
- Base dos Dados, TSE e DataJud (em expansão).

### 3. RAG (Retrieval Augmented Generation) Aprimorado
- Busca semântica e por palavras-chave combinadas.
- Respostas fundamentadas em documentos reais, reduzindo alucinações.
- Citação de fontes (ex: "Segundo a Lei 12.345...").

### 4. Multimodalidade Real
- **Voz**: O ELO ouve áudios e responde em texto (ou áudio).
- **Visão**: O ELO vê fotos de documentos ou problemas urbanos e orienta.

### 5. Infraestrutura Robusta
- **Multi-Provider**: Escolha entre OpenAI e Azure para LLM, TTS e STT.
- **Logs Estruturados**: Logs em JSON para fácil ingestão em ferramentas de observabilidade.
- **Sandbox WhatsApp**: Desenvolva sem precisar de um celular conectado o tempo todo.
- **Testes Automatizados**: Cobertura de testes para garantir a estabilidade das intenções e integrações.

## Próximos Passos
- Expandir conectores do DataHub.
- Implementar notificações ativas (usuário segue um PL e recebe updates).
- Refinar a personalidade do bot com feedback real.
