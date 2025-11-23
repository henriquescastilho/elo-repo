import logging
import os
import re
import tempfile
from dataclasses import dataclass
from typing import Any, Dict, Optional

from backend.app.core.config.bot_identity import BOT_NAME
from backend.app.models.schemas import NormalizedMessage
from backend.app.services import llm_service, pdf_service, stt_service, vision_service

logger = logging.getLogger("elo.oraculo")


URL_PATTERN = re.compile(r"(https?://[^\s]+)", re.IGNORECASE)


@dataclass
class OracleContext:
    """
    Wrapper para enviar ao llm_service no Modo Oráculo.
    Mantém compatibilidade com `answer_user_question` (user_id, type, media_url).
    """

    message: NormalizedMessage
    contexto_oraculo: Dict[str, Any]

    @property
    def user_id(self) -> str:
        return self.message.user_id

    @property
    def type(self) -> str:
        return self.message.type

    @property
    def media_url(self) -> Optional[str]:
        return self.message.media_url

    @property
    def mime_type(self) -> Optional[str]:
        return self.message.mime_type


def _infer_filename(message: NormalizedMessage) -> Optional[str]:
    if message.media_url:
        name = os.path.basename(message.media_url.split("?", 1)[0])
        return name or None
    return None


def _detect_url_from_text(text: str | None) -> Optional[str]:
    if not text:
        return None
    match = URL_PATTERN.search(text)
    if not match:
        return None
    return match.group(1)


async def _build_oracle_context(message: NormalizedMessage) -> Dict[str, Any]:
    """
    Constrói o contexto_oraculo com base no tipo da mensagem e conteúdo.
    """
    context: Dict[str, Any] = {
        "tipo_arquivo": message.type,
        "mime_type": message.mime_type,
        "texto_extraido": "",
        "metadados": {},
    }

    raw_bytes = message.media_bytes or b""

    if message.type == "image":
        logger.info(
            "[ORACULO] tipo=image tamanho=%skb mime=%s",
            round(len(raw_bytes) / 1024, 1),
            message.mime_type,
        )
        description = await vision_service.analyze_image(
            image_bytes=raw_bytes,
            image_url=message.media_url,
        )
        context["texto_extraido"] = description or ""
        context["metadados"] = {
            "origem": "vision_service",
            "media_url": message.media_url,
        }
        logger.info("[ORACULO] visão/imagem construída.")

    elif message.type == "audio":
        logger.info(
            "[ORACULO] tipo=audio tamanho=%skb mime=%s",
            round(len(raw_bytes) / 1024, 1),
            message.mime_type,
        )
        transcript = (message.text or "").strip()
        if not transcript and raw_bytes:
            try:
                with tempfile.NamedTemporaryFile(delete=True, suffix=".ogg") as tmp:
                    tmp.write(raw_bytes)
                    tmp.flush()
                    transcript = await stt_service.transcribe_audio(tmp.name)
            except Exception:
                logger.exception("[ORACULO] Falha ao transcrever áudio no fluxo Oráculo.")
                transcript = ""

        context["texto_extraido"] = transcript or ""
        context["metadados"] = {
            "origem": "stt_service",
            "tem_transcricao": bool(transcript),
        }

    elif message.type == "file":
        # Tenta identificar PDF pelos metadados
        mime = (message.mime_type or "").lower()
        filename = _infer_filename(message)
        logger.info(
            "[ORACULO] tipo=file tamanho=%skb mime=%s filename=%s",
            round(len(raw_bytes) / 1024, 1),
            mime,
            filename,
        )

        is_pdf = mime.startswith("application/pdf") or (
            (message.media_url or "").lower().endswith(".pdf")
        )

        if is_pdf:
            text, meta = pdf_service.extract_text(
                raw_bytes,
                mime_type=message.mime_type,
                filename=filename,
            )
            context["texto_extraido"] = text
            meta["arquivo_tipo"] = "pdf"
            context["metadados"] = meta
            logger.info("[ORACULO] metadados extraídos (PDF): %s", meta)
        else:
            # Tratamento genérico para TXT/HTML/OUTROS
            decoded = ""
            if raw_bytes:
                try:
                    decoded = raw_bytes.decode("utf-8", errors="ignore")
                except Exception:
                    decoded = ""
            context["texto_extraido"] = decoded
            context["metadados"] = {
                "arquivo_tipo": "arquivo_generico",
                "filename": filename,
                "mime_type": message.mime_type,
            }
            logger.info("[ORACULO] metadados extraídos (GENÉRICO): %s", context["metadados"])

    else:
        # Texto puro ou links de notícia
        url = _detect_url_from_text(message.text)
        if url:
            # Importação tardia para evitar dependência circular
            try:
                from backend.app.services import web_scraper  # type: ignore

                logger.info("[ORACULO] Detectado link para análise: %s", url)
                article_text, meta = await web_scraper.fetch_and_extract(url)
                context["texto_extraido"] = article_text
                meta["arquivo_tipo"] = "link"
                context["metadados"] = meta
                logger.info("[ORACULO] metadados extraídos (LINK): %s", meta)
            except Exception:
                logger.exception("[ORACULO] Falha ao extrair conteúdo do link: %s", url)
                context["texto_extraido"] = message.text or ""
                context["metadados"] = {"arquivo_tipo": "texto"}
        else:
            context["texto_extraido"] = message.text or ""
            context["metadados"] = {"arquivo_tipo": "texto"}

    return context


async def handle_message(message: NormalizedMessage) -> str:
    """
    Modo Oráculo: foca exclusivamente no conteúdo enviado (PDF, imagem, áudio, link).
    Sem conselhos emocionais, sem julgamentos – apenas explicação técnica e simples.
    """
    contexto_oraculo = await _build_oracle_context(message)

    # Texto base: se houver pergunta do usuário, ela é prioridade; senão, usamos o texto extraído.
    user_text = (message.text or "").strip() or contexto_oraculo.get("texto_extraido", "")

    logger.info(
        "[ORACULO] enviado ao modelo tipo=%s tamanho_texto=%d",
        contexto_oraculo.get("tipo_arquivo"),
        len(contexto_oraculo.get("texto_extraido") or ""),
    )

    oracle_context = OracleContext(message=message, contexto_oraculo=contexto_oraculo)

    return await llm_service.answer_user_question(
        user_text,
        context=oracle_context,
        flow="oraculo",
        bot_name=BOT_NAME,
    )
