from collections.abc import AsyncIterator
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.router import api_router
from app.db.session import get_db_session


async def override_db_session() -> AsyncIterator[AsyncMock]:
    yield AsyncMock()


@pytest.fixture
def api_client() -> TestClient:
    test_app = FastAPI()
    test_app.include_router(api_router)
    test_app.dependency_overrides[get_db_session] = override_db_session
    return TestClient(test_app)
