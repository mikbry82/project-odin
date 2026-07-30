from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    app: str
    environment: str
    database: Literal["ok", "unavailable"]
