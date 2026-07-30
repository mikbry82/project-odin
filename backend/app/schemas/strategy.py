from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class StrategyBase(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str = ""
    strategy_type: str = "ema_rsi"
    enabled: bool = True
    parameters: dict[str, Any] = Field(default_factory=dict)
    risk_profile: dict[str, Any] = Field(default_factory=dict)


class StrategyCreate(StrategyBase):
    pass


class StrategyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = None
    strategy_type: str | None = None
    enabled: bool | None = None
    parameters: dict[str, Any] | None = None
    risk_profile: dict[str, Any] | None = None


class StrategyResponse(StrategyBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    version: int
    active: bool
    created_at: datetime
    updated_at: datetime


class StrategyEvaluation(BaseModel):
    strategy_id: int
    strategy_name: str
    signal: str
    score: int
    confidence: int
    reasons: list[str]
    risk_profile: dict[str, Any]
