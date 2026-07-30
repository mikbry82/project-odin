from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from app.db.session import get_db_session
from app.main import app


async def override_db_session():
    session = AsyncMock()
    session.execute = AsyncMock(return_value=None)
    yield session


app.dependency_overrides[get_db_session] = override_db_session
client = TestClient(app)


def test_health_check() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["database"] == "ok"
