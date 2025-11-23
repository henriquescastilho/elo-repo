
# ELO Assistente Cidadão

Assistente conversacional focado em acessibilidade cidadã via WhatsApp. Ele orquestra STT, visão computacional, LLM e TTS para receber perguntas por texto, áudio ou imagem e responder com linguagem simples.

## Estrutura do projeto

- `backend/app`: código FastAPI, serviços e integrações (LLM, RAG, DataHub, WhatsApp, TTS/STT/visão).
- `backend/tests`: suíte de testes com Pytest cobrindo intents, DataHub, RAG, LLM orchestration, webhook e fake news.
- `.env.example`: variáveis de configuração (OpenAI/Azure, WAHA, Redis, DataHub, logs).

## Fluxo interno do sistema

1. **Entrada WhatsApp (WAHA/Twilio)**
   - WAHA envia eventos para `POST /webhook/whatsapp`.
   - O webhook (`backend/app/routes/whatsapp_webhook.py`) valida:
     - tipo de evento (`message` / `message.any`);
     - se a mensagem é de chat direto (ignora grupos, newsletters, broadcast);
     - se não é mensagem enviada pelo próprio bot (`fromMe`);
     - se o destinatário corresponde ao `me.id` do WAHA.
   - Normaliza a mensagem em um `NormalizedMessage` (texto / áudio / imagem / arquivo).
   - Para áudio, baixa a mídia via WAHA, chama STT (`stt_service`) e substitui o texto.

2. **Engine de Intenções**
   - `core/router/intents.py` detecta automaticamente o modo:
     - **ELO**: serviços públicos, benefícios, direitos, vida prática.
     - **VOTOS**: projetos de lei, votações, parlamentares, tramitação.
     - **ORÁCULO**: mídia (imagem, áudio, PDF) ou links.
   - Encaminha para o fluxo correspondente em `core/flows`:
     - `elo_flow.handle_message`
     - `votos_flow.handle_message`
     - `oraculo_flow.handle_message`

3. **Modos Lógicos**
   - **Modo ELO**
     - Sempre responde em PT-BR simples.
     - Evita juridiquês e explica passo a passo como acessar serviços públicos.
     - Integra o verificador de fake news (`services/fakenews_service.py`):
       - Risco **alto**: responde com aviso forte + resposta corrigida.
       - Risco **médio**: avisa que está verificando + resposta do ELO.
       - Risco **baixo**: fluxo normal.
   - **Modo VOTOS**
     - Usa RAG **legal_only** via DataHub federado (Câmara + Senado).
     - Explica tramitação e contexto legislativo em linguagem simples.
   - **Modo ORÁCULO**
     - Focado em ler e explicar arquivos/mídia (imagem, PDF, áudio, links).
     - Para PDFs, faz download e extração de texto (`pypdf`).
     - Não usa RAG legislativo direto; prioriza o próprio conteúdo enviado.

4. **RAG e DataHub federado**
   - `services/rag_service.py` decide o modo de busca:
     - `mock`: documentos simulados (ambiente de teste / fallback).
     - `legal_only`: usa `DataHub Aggregator` apenas com Câmara e Senado.
     - `all`: usa todas as fontes do DataHub para contexto amplo.
   - `services/datahub/aggregator.py` consulta em paralelo:
     - Câmara dos Deputados (`camara_service` – `https://dadosabertos.camara.leg.br/api/v2`).
     - Senado Federal (`senado_service` – `https://legis.senado.leg.br/dadosabertos`).
     - Querido Diário (`queridodiario_service` – diários oficiais municipais).
     - Base dos Dados (`basedosdados_service` – `https://basedosdados.org/api/3/action/package_search`).
     - TSE (`tse_service` – dados eleitorais).
     - DataJud (`datajud_service` – processos CNJ).
   - Normaliza todos os documentos para o padrão:
     - `{ id, title, summary, year, source, url, raw_metadata }`
     - Mantém também aliases (`titulo`, `ementa`, `ano`, `link`) usados pelo RAG.
   - Implementa timeouts, `asyncio.gather` e `_fetch_safe` para fallback robusto.

5. **LLM orchestration**
   - `services/llm_service.py`:
     - suporta **OpenAI** público ou **Azure OpenAI** via `llm_provider`;
     - monta prompts em PT-BR simples, com persona “Neto Digital” (`core/llm/prompt_base.py`);
     - injeta histórico de conversa (estado em Redis/memória) e contexto RAG;
     - usa `tenacity` para retries com fallback seguro.

6. **Resposta ao usuário**
   - `services/response_service.py`:
     - sempre envia texto via provider ativo (`whatsapp_provider_waha`, `whatsapp_provider_twilio` ou `whatsapp_provider_console`);
     - opcionalmente gera áudio TTS (`core/tts/service.py` → `tts_service`) e manda como segunda mensagem;
     - evita “double send”: o fluxo VOTOS já envia diretamente (e marca `delivered=True`), ELO/ORÁCULO retornam apenas texto e o webhook envia uma vez.

## Como rodar (local)

Pré‑requisitos:
- Python 3.10+ (idealmente 3.11+).
- Redis opcional (para cache).

1. Clonar e preparar ambiente:

   ```bash
   git clone <repo>
   cd versao_final
   cp .env.example .env
   ```

2. Criar venv e instalar dependências:

   ```bash
   cd backend
   python -m venv .venv
   source .venv/bin/activate  # Linux/macOS
   # .venv\Scripts\activate   # Windows (PowerShell/cmd)

   pip install -r ../requirements.txt
   ```

3. Subir Redis (opcional, mas recomendado):

   - Via Docker simples:

     ```bash
     docker run -p 6379:6379 redis:alpine
     ```

   - Ajuste `REDIS_URL=redis://localhost:6379/0` no `.env`.

4. Rodar FastAPI:

   ```bash
   uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
   ```

5. Testar health:

   ```bash
   curl http://localhost:8000/health
   ```

## Como rodar com Docker / Docker Compose

Ambiente de desenvolvimento com WAHA + backend + Redis:

```bash
docker-compose up --build
```

Serviços:
- `backend`: FastAPI em `http://localhost:8000`.
- `waha`: painel WAHA em `http://localhost:3000`.
- `redis`: cache em `localhost:6379`.

Em produção, use `docker-compose.prod.yaml`:

```bash
docker-compose -f docker-compose.prod.yaml up --build -d
```

## Configurando Azure OpenAI / OpenAI

As principais variáveis estão em `.env.example`:

- Azure:
  - `AZURE_OPENAI_API_KEY`
  - `AZURE_OPENAI_ENDPOINT`
  - `AZURE_OPENAI_API_VERSION`
  - `AZURE_DEPLOYMENT_NAME` (ex.: `gpt-5-mini` ou `gpt-4oElo`)
  - `AZURE_TTS_DEPLOYMENT_NAME`
  - `AZURE_STT_DEPLOYMENT_NAME`
- Opcional OpenAI público:
  - `OPENAI_API_KEY`
  - `OPENAI_API_BASE` (se usar endpoint compatível).

Modelos principais:
- `LLM_MODEL_NAME` – ex.: `gpt-5-mini` (Azure) ou similar.
- `TTS_MODEL_NAME` – ex.: `gpt-4o-mini-tts`.
- `STT_MODEL_NAME` – ex.: `whisper-1`.
- `VISION_MODEL_NAME` – ex.: `gpt-4o`.

O provider é selecionado por:
- `LLM_PROVIDER=azure|openai`
- `TTS_PROVIDER=azure|openai`
- `STT_PROVIDER=azure|openai`
- `VISION_PROVIDER=azure|openai`

Nunca versione o arquivo `.env` nem exponha suas chaves.

## Configurando WAHA e WhatsApp

1. Subir WAHA (já configurado em `docker-compose.yml`):
   - Painel: `http://localhost:3000`.
   - Credenciais padrão (ajuste no compose):
     - `WAHA_DASHBOARD_USERNAME`
     - `WAHA_DASHBOARD_PASSWORD`

2. Configurar sessão WhatsApp (no painel WAHA):
   - Criar/usar sessão `default` (é o padrão esperado pelo backend).
   - Escanear o QR code com o WhatsApp.

3. Configurar callback do WAHA:
   - URL do callback (no painel WAHA):
     - Em ambiente Docker local:
       - `http://host.docker.internal:8000/webhook/whatsapp`
     - Em produção (atrás de Nginx, por exemplo):
       - `https://seu-dominio.com/webhook/whatsapp`

4. Variáveis de ambiente relacionadas:
   - `.env`:
     - `WHATSAPP_PROVIDER=waha`
     - `WAHA_BASE_URL=http://waha:3000` (ajustado no `docker-compose.yml`).
     - `WAHA_API_TOKEN=<mesma API key configurada no WAHA>`.
     - `WHATSAPP_SANDBOX_MODE=false` em produção.

No código:
- Envio de mensagens:
  - `infra/waha_client.py` chama `/api/sendText`, `/api/sendVoice`, `/api/sendImage`.
  - `services/whatsapp_provider_waha.py` centraliza a lógica para texto/áudio.
- Healthcheck WAHA:
  - `GET /debug/waha-health` retorna status da sessão WAHA.

## Webhook de WhatsApp (WAHA / Twilio)

- Endpoint principal: `POST /webhook/whatsapp`.
- Payload esperado (WAHA):
  - `event`: `"message"` ou `"message.any"`.
  - `payload.from`, `payload.to`, `payload.body`, `payload.type`, `payload.fromMe`, `payload.media` (opcional).
  - `me.id`: ID do bot para validar destinatário.
- Segurança e robustez:
  - Ignora grupos, newsletters e mensagens enviadas pelo próprio bot.
  - Deduplicação de mensagens via Redis (`cache_service.is_duplicate_message`).
  - Tratamento de timeouts ao baixar mídia / transcrever áudio.
  - Logs detalhados com prefixo `[WAHA]`.

## Testes automatizados

Rodar toda a suíte:

```bash
cd backend
pytest
```

Cobertura principal:
- **Intent Engine** – detecção automática ELO / VOTOS / ORÁCULO.
- **DataHub federado** – conectores individuais + agregador.
- **RAG** – modos `legal_only` e `all`.
- **LLM orchestration** – troca de provider OpenAI/Azure mockada.
- **Fake news detector** – `fakenews_service` com mocks de DataHub e LLM.
- **WhatsApp webhook** – fluxo de health, console provider e integrações básicas.

## Resumo do que foi auditado/corrido

- Integração LLM (OpenAI/Azure) consolidada em `llm_service`, com retries e fallback.
- DataHub federado normalizando documentos para `{id, title, summary, year, source, url, raw_metadata}`.
- Novo módulo de verificação de fake news integrado ao fluxo ELO.
- Ajustes de RAG no modo VOTOS (`legal_only` com Câmara + Senado).
- WAHA alinhado via `WAHA_BASE_URL` no `docker-compose.yml` e health em `/debug/waha-health`.
- Suíte Pytest passando 100%, incluindo novos testes de fake news.
