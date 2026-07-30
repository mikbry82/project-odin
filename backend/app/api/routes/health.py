from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db_session
from app.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check(
    session: AsyncSession = Depends(get_db_session),
) -> HealthResponse:
    database_status = "ok"
    try:
        await session.execute(text("SELECT 1"))
    except Exception:
        database_status = "unavailable"

    return HealthResponse(
        app=settings.app_name,
        environment=settings.app_env,
        database=database_status,
    )
