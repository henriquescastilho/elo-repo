import logging
from html import unescape
from typing import Dict, Tuple

import httpx

logger = logging.getLogger(__name__)


def _strip_tags(html: str) -> str:
    """
    Remove de forma simples tags HTML para obter texto bruto.
    (Evita dependência extra como BeautifulSoup.)
    """
    import re

    text = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = unescape(text)
    return " ".join(text.split())


async def fetch_and_extract(url: str) -> Tuple[str, Dict[str, object]]:
    """
    Busca uma página web (ex: notícia) e extrai texto bruto e metadados básicos.
    Não faz resumo – essa função apenas prepara o material para o Modo Oráculo.
    """
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, follow_redirects=True)
            resp.raise_for_status()
    except Exception as exc:
        logger.exception("Falha ao buscar URL para Oráculo: %s", exc)
        return "", {"url": url, "status": "erro_http"}

    html = resp.text or ""

    # Título simples
    import re

    title_match = re.search(r"<title>(.*?)</title>", html, flags=re.IGNORECASE | re.DOTALL)
    title = unescape(title_match.group(1).strip()) if title_match else ""

    text = _strip_tags(html)
    # Limita tamanho para não estourar prompt
    max_chars = 20000
    if len(text) > max_chars:
        text = text[:max_chars]

    metadata: Dict[str, object] = {
        "url": url,
        "title": title,
        "length": len(text),
    }
    logger.info("[ORACULO] Web scraper extraiu %d caracteres de %s", len(text), url)
    return text, metadata

