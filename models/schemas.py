from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AgentInvokeRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)


class AgentStep(BaseModel):
    action: str
    success: bool
    message: str
    payload: dict[str, Any] | None = None


class AgentInvokeResponse(BaseModel):
    result: str
    success: bool
    steps: list[AgentStep]
    intent: list[str] = Field(default_factory=list)
    planner_reasoning: str | None = None


class HealthResponse(BaseModel):
    status: str
