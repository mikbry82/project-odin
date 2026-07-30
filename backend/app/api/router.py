from fastapi import APIRouter

from app.api.routes import ai_engine, markets, paper, scanner, strategies, system

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(system.router)
api_router.include_router(markets.router)
api_router.include_router(paper.router)
api_router.include_router(scanner.router)
api_router.include_router(ai_engine.router)
api_router.include_router(strategies.router)
