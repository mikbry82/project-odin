from datetime import datetime

from pydantic import BaseModel


class AgentAssessment(BaseModel):
    agent: str
    title: str
    verdict: str
    score: int
    confidence: int
    status: str
    summary: str
    evidence: list[str]
    warnings: list[str]


class ChiefDecision(BaseModel):
    verdict: str
    score: int
    confidence: int
    risk_level: str
    position_size_percent: float
    summary: str
    reasons: list[str]
    warnings: list[str]


class AIAnalysisResponse(BaseModel):
    symbol: str
    display_symbol: str
    interval: str
    price: float
    source: str
    agents: list[AgentAssessment]
    chief: ChiefDecision
    generated_at: datetime
