# Guia Rápido – Canal Telegram

## Variáveis de Ambiente
- `TELEGRAM_ENABLED`: ativa/desativa o envio real (default: `False`).
- `TELEGRAM_BOT_TOKEN`: token do bot.
- `TELEGRAM_WEBHOOK_SECRET`: opcional, header `X-Telegram-Bot-Api-Secret-Token` deve bater.
- `TELEGRAM_BASE_URL`: normalmente `https://api.telegram.org`.
- `TELEGRAM_SANDBOX_MODE`: evita chamadas reais para API (default: `True`).

## Teste Local
1. Suba o backend: `uvicorn backend.app.main:app --reload`.
2. Healthcheck: `curl http://localhost:8000/health`.
3. Simule mensagem:  
   `curl -X POST http://localhost:8000/webhook/telegram -H "Content-Type: application/json" -d '{ "update_id": 1, "message": { "message_id": 1, "chat": { "id": 123456 }, "text": "teste telegram" } }'`

## Observações
- Em sandbox, o provider só loga o payload a ser enviado.
- `user_id` no pipeline vira `tg:<chat_id>`, mantendo compatibilidade com intents/flows.
- Respostas saem pelo `telegram_provider` (texto e, se habilitado, áudio gerado pelo TTS).
