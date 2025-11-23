import io
import logging
from typing import Dict, Tuple, Optional

import pypdf

logger = logging.getLogger(__name__)


def _clean_text(text: str) -> str:
    """
    Remove caracteres de controle e sequências claramente inválidas.
    Mantém quebras de linha básicas para leitura.
    """
    if not text:
        return ""
    cleaned_chars = []
    for ch in text:
        if ch == "\n" or ch == "\t" or ch == " ":
            cleaned_chars.append(ch)
        elif ch.isprintable():
            cleaned_chars.append(ch)
    cleaned = "".join(cleaned_chars)
    return " ".join(cleaned.split())


def _fallback_decode_bytes(raw: bytes) -> str:
    """
    Fallback bem simples para tentar extrair algo legível mesmo se o PDF estiver corrompido.
    """
    if not raw:
        return ""
    for enc in ("utf-8", "latin-1"):
        try:
            return raw.decode(enc, errors="ignore")
        except Exception:
            continue
    return ""


def extract_text(
    pdf_bytes: bytes,
    mime_type: Optional[str] = None,
    filename: Optional[str] = None,
) -> Tuple[str, Dict[str, object]]:
    """
    Extrai texto de um PDF usando pypdf com fallback simples baseado em decodificação
    de bytes e, opcionalmente, detecção de idioma via `lingua` se estiver instalada.

    Retorna (texto_limpo, metadados).
    """
    metadata: Dict[str, object] = {
        "filename": filename,
        "mime_type": mime_type,
        "num_pages": 0,
        "language": None,
        "extraction_method": "pypdf",
    }

    if not pdf_bytes:
        logger.warning("extract_text chamado com pdf_bytes vazio.")
        return "", metadata

    text = ""
    try:
        reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        pages_text = []
        for page in reader.pages:
            metadata["num_pages"] = metadata.get("num_pages", 0) + 1
            try:
                page_text = page.extract_text() or ""
            except Exception:
                page_text = ""
            if page_text:
                pages_text.append(page_text)
        text = "\n".join(pages_text)
        logger.info("[ORACULO] Extraído texto de PDF com pypdf: %d caracteres", len(text))
    except Exception as exc:
        logger.exception("Falha ao extrair texto de PDF com pypdf: %s", exc)
        text = ""

    if not text.strip():
        # Fallback: tenta ao menos decodificar os bytes crus.
        metadata["extraction_method"] = "fallback_bytes"
        raw_text = _fallback_decode_bytes(pdf_bytes)
        text = raw_text

    # Tenta detectar idioma com lingua, se disponível (metadado apenas).
    if text.strip():
        try:
            from lingua import Language, LanguageDetectorBuilder  # type: ignore

            languages = [Language.PORTUGUESE, Language.ENGLISH, Language.SPANISH]
            detector = LanguageDetectorBuilder.from_languages(*languages).build()
            detected = detector.detect_language_of(text)
            metadata["language"] = detected.name if detected else None
        except Exception:
            # Não é crítico para o fluxo Oráculo.
            logger.debug("Falha ao detectar idioma com lingua (opcional).", exc_info=True)

    cleaned = _clean_text(text)
    return cleaned, metadata

