"""Health-Check Endpoint."""
from fastapi import APIRouter

router = APIRouter(tags=["misc"])


@router.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "nadini-meeting"}
