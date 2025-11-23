# Arquitetura – ELO Assistente Cidadão 2.0

## Visão Geral
O **ELO Assistente Cidadão** é um sistema de IA cívica projetado para democratizar o acesso à informação legislativa e serviços públicos. A versão 2.0 introduz uma arquitetura federada, detecção automática de intenção e integração profunda com múltiplos provedores de dados.

## Componentes Principais

### 1. Core & Router (`backend/app/core`)
- **Intent Engine (`core/router/intents.py`)**: Analisa cada mensagem e decide automaticamente o modo de operação:
  - **ELO**: Dúvidas sobre serviços, direitos e cidadania.
  - **VOTOS**: Consultas sobre projetos de lei, votações e parlamentares.
  - **ORÁCULO**: Processamento de mídia (áudio, imagem, documentos) e links externos.
- **Bot Identity (`core/config/bot_identity.py`)**: Define a persona e o tom de voz (PT-BR simples, acolhedor).

### 2. DataHub Federado (`backend/app/services/datahub`)
Camada de abstração que unifica múltiplas fontes de dados públicos:
- **Aggregator**: Orquestra consultas paralelas e normaliza resultados.
- **Conectores**:
  - `camara_service`: API da Câmara dos Deputados.
  - `senado_service`: API do Senado Federal.
  - `queridodiario_service`: Diários Oficiais municipais.
  - `basedosdados_service`: Estatísticas e dados estruturados.
  - `tse_service`: Dados eleitorais.
  - `datajud_service`: Jurisprudência e processos.
- **Cobertura completa recomendada**: usar `LEGAL_DATA_SOURCE_MODE=all` para puxar tudo destas fontes:
  - Câmara: https://dadosabertos.camara.leg.br/swagger/api.html
  - Senado: https://www12.senado.leg.br/dados-abertos
  - Querido Diário: https://queridodiario.ok.org.br/tecnologia/api
  - Base dos Dados: https://basedosdados.org/

### 3. RAG Avançado (`backend/app/services/rag_service.py`)
Sistema de Recuperação Aumentada por Geração:
- **Embeddings**: OpenAI `text-embedding-3-small`.
- **Vector Store**: FAISS (local) ou RedisVL.
- **Fluxo**:
  1. Recebe query do usuário.
  2. Busca documentos relevantes no DataHub (federado).
  3. Classifica e filtra os melhores resultados.
  4. Injeta contexto no prompt do LLM.

### 4. Integração LLM (`backend/app/services/llm_service.py`)
- **Multi-Provider**: Suporte híbrido para **OpenAI** e **Azure OpenAI**.
- **Factory Pattern**: Abstração que permite troca de provedor via configuração (`LLM_PROVIDER`, `TTS_PROVIDER`, `STT_PROVIDER`).
- **Prompt Engineering**: Prompts dinâmicos baseados no modo (ELO/VOTOS/ORÁCULO) e contexto recuperado.
- **Cache**: Redis para evitar custos repetitivos em perguntas frequentes.

### 5. Canais & Multimídia
- **WhatsApp Provider**:
  - **WAHA (WhatsApp HTTP API)**: Principal gateway.
  - **Console/Sandbox**: Para desenvolvimento e testes sem celular.
- **Telegram Provider**:
  - Webhook dedicado em `/webhook/telegram` (com secret opcional).
  - Provider próprio (`telegram_provider`) para `sendMessage`, `sendAudio`, `sendPhoto`, respeitando sandbox.
- **Multimodalidade**:
  - **TTS**: Geração de áudio para respostas (OpenAI Audio).
  - **STT**: Transcrição de mensagens de voz (Whisper).
  - **Vision**: Análise de imagens enviadas pelo usuário (GPT-4o Vision).

## Fluxo de Dados

1. **Entrada**: Webhook recebe mensagem (`POST /webhook/whatsapp` ou `POST /webhook/telegram`).
2. **Roteamento**: `dispatch_message` detecta intenção.
3. **Processamento**:
   - Se **ORÁCULO**: Processa mídia/link diretamente.
   - Se **VOTOS**: Aciona DataHub para buscar dados legislativos + RAG.
   - Se **ELO**: Aciona RAG para base legal de direitos (se necessário) ou responde com conhecimento geral.
4. **Geração**: LLM gera resposta em linguagem simples com base no contexto.
5. **Saída**: Texto (e opcionalmente áudio) enviado via Provider (WAHA/Twilio/Console ou Telegram).

## Infraestrutura
- **Backend**: FastAPI (Python 3.11+).
- **Container**: Docker + Docker Compose.
- **Cache**: Redis.
- **Dependências Externas**: APIs Públicas (Câmara, Senado, etc.), OpenAI API.
