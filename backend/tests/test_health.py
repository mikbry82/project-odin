from unittest.mock import AsyncMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes.health import router
from app.db.session import get_db_session


async def override_db_session():
    session = AsyncMock()
    session.execute = AsyncMock(return_value=None)
    yield session


def test_health_check() -> None:
    test_app = FastAPI()
    test_app.include_router(router)
    test_app.dependency_overrides[get_db_session] = override_db_session
    client = TestClient(test_app)

    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["database"] == "ok"
