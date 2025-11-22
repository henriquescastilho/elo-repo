# RAIO X – ELO Assistente Cidadão

## Visão rápida
- **Stack principal:** FastAPI (`backend/app/main.py`) expondo rotas de saúde/debug e o webhook de WhatsApp.
- **Provedores WhatsApp:** WAHA (padrão) e alternativa Twilio.
- **IA & voz:** Serviços de LLM, TTS, STT e visão estão definidos como *placeholders* aguardando integração real (OpenAI/ElevenLabs).
- **RAG:** Busca simulada de documentos legais, com opção de API da Câmara e LangChain/FAISS opcional.
- **Cache e estado:** Redis opcional para cache de respostas e estado de usuário; fallback em memória.
- **Notificações externas:** Integração com n8n desativada nesta versão; apenas hooks internos/logs para futuras notificações.

## Diagrama textual de arquitetura
```
[Usuário WhatsApp]
      |
      v
WAHA -> POST /webhook/whatsapp (FastAPI)
      |  - Filtra eventos message/message.any, ignora mensagens do bot e grupos
      |  - Valida destinatário (me.id) e texto
      |  - Constrói reply simples e envia via provider configurado
      |
      +--> whatsapp_provider_waha.send_message() -> WAHA /api/sendText
      |
      +--> whatsapp_provider_twilio.send_message() -> Twilio API (fallback)
```

## APIs e rotas FastAPI
- `backend/app/main.py`: cria o app FastAPI e inclui rotas.
- `GET /health` (`backend/app/routes/health.py`): healthcheck simples.
- `GET /debug/ping` (`backend/app/routes/debug.py`): devolve status e provider configurado.
- `POST /webhook/whatsapp` (`backend/app/routes/whatsapp_webhook.py`): entrada WAHA/Twilio; valida evento, remetente, destinatário e texto; responde ecoando a mensagem.

## Módulos e responsabilidades
- `backend/app/config.py`: `Settings` com OpenAI, TTS/STT, WAHA, Twilio, Redis, APIs legislativas e log level (sem n8n obrigatório).
- `backend/app/core/logging.py`: configuração global de logging.
- `backend/app/core/exceptions.py`: erros base (`ServiceError`, `ProviderError`).
- `backend/app/models/schemas.py`: `NormalizedMessage` (texto/áudio/imagem) e `OutgoingMessage`.
- `backend/app/services/whatsapp_provider_waha.py`: envio via WAHA `/api/sendText`, headers `x-api-key`, retries; áudio ainda não suportado.
- `backend/app/services/whatsapp_provider_twilio.py`: envio via Twilio Messages API com `MediaUrl` opcional.
- `backend/app/services/llm_service.py`: monta prompt básico e chama RAG; cacheia respostas; integração real com LLM pendente.
- `backend/app/services/rag_service.py`: busca mock ou API da Câmara; suporte opcional a LangChain/FAISS e embeddings OpenAI.
- `backend/app/services/cache_service.py`: cache/estado em Redis ou memória.
- `backend/app/services/tts_service.py`: geração de áudio (mock) via OpenAI/ElevenLabs pendente.
- `backend/app/services/stt_service.py`: transcrição de áudio (mock) via Whisper ou similar pendente.
- `backend/app/services/vision_service.py`: descrição de imagem/pergunta (mock) via LLM multimodal.
- `backend/app/services/notifications_service.py`: stubs de notificação que apenas fazem log; integração externa opcional/desativada.

## Fluxos de conversa existentes
- `POST /webhook/whatsapp`: único fluxo ativo; responde com eco “Recebi sua mensagem…” e validações básicas (ignora grupos/newsletter, mensagens do próprio bot e destinos diferentes).
- LLM/TTS/STT/visão ainda não estão conectados ao webhook; `llm_service.answer_user_question` é usado apenas em testes.

## Pontos de integração com WAHA
- **Webhook de mensagem:** WAHA envia para `POST /webhook/whatsapp` com campos `event`, `payload.from`, `payload.to`, `payload.body`, `payload.fromMe`, além de `me.id` para validar destinatário.
- **Envio de texto:** `whatsapp_provider_waha.send_message` chama `POST {WAHA_BASE_URL}/api/sendText` com JSON `{chatId, text, session}` e header `x-api-key`.
- **Áudio/imagens:** ainda não implementados; função aceita `audio_url` mas ignora caso seja mock.
- **Provedores alternativos:** `whatsapp_provider_twilio.send_message` usa Twilio se `Settings.whatsapp_provider` for `"twilio"`.

## Integração com OpenAI / IA
- **LLM:** `llm_service.answer_user_question` monta prompt em PT-BR e usa `rag_service` para contexto. Chamada real ao provider ainda TODO (usa settings `llm_provider`, `openai_api_key`, `openai_api_base`).
- **TTS/STT:** módulos placeholders com logs e TODO para OpenAI/ElevenLabs/Whisper.
- **Visão:** placeholder para GPT-4o ou similar, retornando texto simulado.
