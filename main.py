from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException

from db.database import init_db
from models.schemas import AgentInvokeRequest, AgentInvokeResponse, HealthResponse
from orchestrator.agent import OrchestratorAgent


load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("agentflow")


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="AgentFlow Productivity Assistant",
    version="1.0.0",
    description="Multi-agent productivity API with orchestrator, sub-agents, MCP tool integration, and DB persistence.",
    lifespan=lifespan,
)

orchestrator = OrchestratorAgent()


@app.get("/health")
async def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.post("/invoke", response_model=AgentInvokeResponse)
async def invoke_endpoint(payload: AgentInvokeRequest) -> AgentInvokeResponse:
    try:
        logger.info("Received query with %d chars", len(payload.query))
        result = await orchestrator.run(payload.query)
        return AgentInvokeResponse(**result)
    except Exception as exc:
        logger.exception("Invoke endpoint failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/agent", response_model=AgentInvokeResponse)
async def agent_endpoint(payload: AgentInvokeRequest) -> AgentInvokeResponse:
    return await invoke_endpoint(payload)
