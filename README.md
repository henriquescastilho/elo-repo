
# ELO Assistente Cidadão

Assistente conversacional focado em acessibilidade cidadã via WhatsApp. Ele orquestra STT, visão computacional, LLM e TTS para receber perguntas por texto, áudio ou imagem e responder com linguagem simples.

## Estrutura

- `backend/app`: código FastAPI, serviços e integrações
- `backend/tests`: testes básicos com Pytest
- `.env.example`: variáveis de configuração

## Como funciona o ELO – Assistente Cidadão
- FastAPI recebe mensagens do WhatsApp via WAHA/Twilio no `POST /webhook/whatsapp`.
- O roteador de intenções (`core/router/intents.py`) decide se a conversa é do fluxo **ELO** (serviços públicos/direitos) ou **VOTOS** (plenário, deputados, votações) e chama o fluxo correspondente.
- Respostas usam um prompt base em português simples (`core/llm/prompt_base.py`) com instruções específicas por fluxo e um RAG básico (`services/rag_service.py`).
- Envio de respostas passa por `services/response_service.py`, que sempre envia texto e pode enviar áudio gerado por TTS.

## Módulo VOTOS Interativo
- Detecta palavras-chave de parlamento/plenário/deputados no texto do usuário.
- Responde usando o mesmo prompt base, com foco em explicar votações e acompanhamento do plenário.
- Pode ser estendido para consultar APIs da Câmara/Senado via `rag_service`.

## Dependências principais

- Python 3.11+
- FastAPI / Uvicorn
- Redis (para cache semântico, opcional)

## Configuração

1. Copie o arquivo de variáveis e preencha os valores conforme seu ambiente:

   ```bash
   cp .env.example .env
   ```

2. Instale as dependências (sugestão com pip):

   ```bash
   cd backend
   python -m venv .venv
   source .venv/bin/activate
   pip install fastapi uvicorn[standard] pydantic pydantic-settings httpx pytest redis
   ```

3. Execute o backend com Uvicorn:

   ```bash
   uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
   ```

4. Teste o endpoint de saúde:

   ```bash
   curl http://localhost:8000/health
   ```

5. Integração com orquestradores externos (ex.: n8n) é opcional e está desativada nesta versão. Toda a lógica de fluxo roda no backend (FastAPI + LLM).

6. (Opcional) Para habilitar re-ranking com LangChain/FAISS, defina `LANGCHAIN_ENABLED=true` e instale também `langchain-community`, `langchain-openai` e `faiss-cpu`.

7. (Opcional) Áudio de resposta:
   - Ajuste `SEND_AUDIO_DEFAULT=true` em `.env` para sempre enviar áudio além do texto.
   - Garanta configuração de TTS (`tts_provider`, `openai_api_key` ou `elevenlabs_api_key/voice_id`) e WAHA/Twilio ativos.

## Configurando a OpenAI (chaves)

- Crie uma API key no painel da OpenAI (e, se quiser, associe a um projeto).
- Copie a chave **apenas** para o arquivo `.env` (não commitar no Git).

Exemplo:

```bash
cp .env.example .env
# editar .env e preencher:
# OPENAI_API_KEY=sk-...
```

Nunca compartilhe sua chave e não versione o arquivo `.env`.

## Testes

Execute os testes unitários básicos:

```bash
cd backend
pytest
```
```bash
cd backend
pytest
```

