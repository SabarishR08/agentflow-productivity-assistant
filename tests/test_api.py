from __future__ import annotations

from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_invoke_endpoint_contract() -> None:
    response = client.post("/invoke", json={"query": "list tasks"})
    assert response.status_code == 200

    body = response.json()
    assert "result" in body
    assert "success" in body
    assert "steps" in body
    assert "intent" in body
    assert "planner_reasoning" in body


def test_agent_alias_endpoint_contract() -> None:
    response = client.post("/agent", json={"query": "list tasks"})
    assert response.status_code == 200
