# Resumo das mudanças – ELO Assistente Cidadão

## O que foi alterado
- Documentação inicial de arquitetura (`docs/RAIO_X_ELO.md`) e detalhamento atualizado (`docs/ARQUITETURA_ELO.md`).
- Identidade única do bot (`core/config/bot_identity.py`) com projetos: ELO Assistente Cidadão e VOTOS Interativo.
- Camada de roteamento de intenções (`core/router/intents.py`) que normaliza texto e distingue fluxos ELO vs VOTOS.
- Fluxos separados (`core/flows/elo_flow.py`, `core/flows/votos_flow.py`) integrados ao webhook do WhatsApp.
- Cliente WAHA centralizado (`infra/waha_client.py`) para texto/voz/imagem com retries.
- Provider WAHA atualizado para usar o cliente central; Twilio mantido.
- Prompt base em PT-BR simples (`core/llm/prompt_base.py`) aplicado no `llm_service`.
- Camada de resposta com texto e áudio (`services/response_service.py`) usando TTS (`core/tts/service.py`) e flag `SEND_AUDIO_DEFAULT`.
- README ampliado com visão rápida dos fluxos e do módulo VOTOS.
- Dependência de n8n removida: notificações são internas (logs) e qualquer orquestrador externo é opcional/desativado.

## Onde estão os fluxos principais
- `POST /webhook/whatsapp` → normaliza mensagem → `dispatch_message` → `elo_flow` ou `votos_flow` → `llm_service` (prompt base + RAG) → `response_service`.
- Fluxo ELO: orientações sobre serviços públicos e direitos, linguagem simples.
- Fluxo VOTOS: votações, plenário, deputados/senadores, também com linguagem simples.

## Integração de áudio
- Flag `SEND_AUDIO_DEFAULT` em `backend/app/config.py`.
- `response_service.responder_usuario` sempre envia texto; se áudio habilitado ou solicitado (`modo="texto+audio"`), chama TTS (`core/tts/service.py` → `services/tts_service.py`) e envia via WAHA/Twilio.
- WAHA: `infra/waha_client.send_voice` converte áudio se necessário e usa `/api/sendVoice`.

## Convivência dos dois projetos no mesmo bot
- Roteador de intenções decide dinamicamente ELO vs VOTOS sem alterar a rota pública (`/webhook/whatsapp`).
- Identidade e projetos padronizados em config, evitando strings soltas.
- Prompt único garante tom consistente nos dois fluxos; cada fluxo adiciona instruções específicas.
- Envio unificado (texto/áudio) via `response_service` e cliente WAHA centralizado, mantendo compatibilidade com Twilio.
