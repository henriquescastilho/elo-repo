from fastapi import APIRouter, Query
from backend.app.infra import waha_client
from backend.app.services import response_service

router = APIRouter(prefix="/debug", tags=["debug"])

@router.get("/waha-health")
async def waha_health():
    """
    Check WAHA connection health.
    """
    return await waha_client.check_health()

@router.post("/provider-test")
async def provider_test(to: str = "5511999999999@c.us", text: str = "ping"):
    """
    Send a test message using the active provider.
    """
    try:
        result = await response_service.responder_usuario(to, text, mode="texto")
        return {"status": "ok", "provider_status": "delivered", "details": result}
    except Exception as exc:
        return {"status": "ok", "provider_status": "failed", "error": str(exc)}


@router.get("/rag/federado")
async def debug_rag_federado(query: str):
    """
    Debug: Test federated search across all DataHub sources.
    """
    from backend.app.services.datahub import aggregator
    results = await aggregator.search_all_sources(query)
    return {
        "query": query,
        "count": len(results),
        "results": results
    }
