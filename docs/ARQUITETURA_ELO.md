# Arquitetura – ELO Assistente Cidadão

## Visão geral
- **App FastAPI** (`backend/app/main.py`) expõe rotas:
  - `GET /health`
  - `GET /debug/ping`
  - `POST /webhook/whatsapp` (entrada WAHA/Twilio)
- **Identidade do bot**: `core/config/bot_identity.py` define `BOT_NAME` e projetos (`ELO Assistente Cidadão`, `VOTOS Interativo`).
- **Roteamento de intenções**: `core/router/intents.py` normaliza texto, detecta intenção (ELO ou VOTOS) e despacha para `core/flows/elo_flow.py` ou `core/flows/votos_flow.py`.
- **Fluxos**:
  - `elo_flow`: perguntas de serviços públicos/direitos.
  - `votos_flow`: votações, plenário, deputados.
- **LLM**: `services/llm_service.py` usa `core/llm/prompt_base.py` + RAG (`services/rag_service.py`) e cache (`services/cache_service.py`).
- **WAHA client**: `infra/waha_client.py` centraliza `send_text`, `send_voice`, `send_image`.
- **Providers WhatsApp**: `services/whatsapp_provider_waha.py` e `services/whatsapp_provider_twilio.py` chamam o cliente centralizado ou a API Twilio.
- **Resposta ao usuário**: `services/response_service.py` envia texto e opcionalmente áudio via TTS (`core/tts/service.py` + `services/tts_service.py`).
- **STT/Visão**: `services/stt_service.py` e `services/vision_service.py` (placeholders).
- **Notificações**: `services/notifications_service.py` apenas faz logs internos; integração com n8n está desativada/ opcional.

## Fluxo principal de mensagem
1. WAHA envia evento `message`/`message.any` para `POST /webhook/whatsapp`.
2. Handler valida remetente, destino e texto; normaliza conteúdo.
3. `dispatch_message` decide intenção (VOTOS se palavras-chave de parlamento; senão ELO).
4. Fluxo selecionado chama `llm_service.answer_user_question` com prompt base e instruções do fluxo.
5. `response_service.responder_usuario` envia texto via provedor configurado; se `settings.send_audio_default` ou modo `texto+audio`, gera TTS e envia áudio via WAHA/Twilio.

## Pontos WAHA
- **Webhook**: `POST /webhook/whatsapp` consome payload WAHA (`event`, `payload.*`, `me.id`).
- **Envio de texto**: `infra/waha_client.send_text` → `POST {WAHA_BASE_URL}/api/sendText`.
- **Envio de voz**: `infra/waha_client.send_voice` converte se necessário (`/api/{session}/media/convert/voice`) e chama `/api/sendVoice`.
- **Envio de imagem**: `infra/waha_client.send_image` → `/api/sendImage` (com caption opcional).

## Prompt e linguagem
- `core/llm/prompt_base.py`: instruções de sistema em PT-BR simples; sem juridiquês.
- Fluxos adicionam instruções específicas (ELO vs VOTOS) antes de gerar resposta.

## Configuração chave (`backend/app/config.py`)
- `whatsapp_provider` (`waha`/`twilio`), `waha_base_url`, `waha_api_token`, `waha_session_name`.
- `openai_api_key/openai_api_base`, `llm_provider`, `tts_provider`, `stt_provider`.
- `send_audio_default`: habilita áudio adicional por padrão.
- `redis_url` (cache), `api_camara_base_url`.

## Diferencial
- O ELO não depende de ferramentas low-code externas (como n8n); toda a orquestração roda no backend integrando WAHA + FastAPI + LLM/TTS.
