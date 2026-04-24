import os

os.environ.setdefault(
    "DB_URI", "sqlite:///./test.db"
)

from fastapi.testclient import TestClient

from app.ai.schemas.graph_schema import GraphOutput
from app.config.db import get_db
from app.routes import chatRoute
from app.routes.chatRoute import get_agent
from main import app


class FakeAgent:
    async def run(self, user_id, question, history=None):
        return GraphOutput(
            answer="Used no tools. Test answer.",
            reasoning="No tool was needed.",
            sources=[],
            latency_ms={
                "total": 1,
                "by_step": {
                    "retrieve": 0,
                    "llm": {"planner": 1, "response": 0, "total": 1},
                },
            },
            tokens={
                "planner": {"input": 1, "output": 1},
                "response": {"input": 0, "output": 0},
                "total": {"input": 1, "output": 1},
            },
        )


class FakeDb:
    def add(self, item):
        return None

    def commit(self):
        return None

    def refresh(self, item):
        item.id = 1

    def close(self):
        return None


def override_db():
    yield FakeDb()


def test_chat_route_rejects_empty_question():
    client = TestClient(app)

    response = client.post(
        "/chat",
        json={"question": "   ", "account_id": 1, "user_id": 1},
    )

    assert response.status_code == 400


def test_chat_route_returns_graph_output_with_mocked_agent(monkeypatch):
    monkeypatch.setattr(chatRoute, "get_history", lambda *args, **kwargs: [])
    monkeypatch.setattr(chatRoute, "save_message", lambda *args, **kwargs: None)
    app.dependency_overrides[get_agent] = lambda: FakeAgent()
    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)

    response = client.post(
        "/chat",
        json={"question": "hello", "account_id": 1, "user_id": 1},
    )

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["reasoning"] == "No tool was needed."


def test_health_route_does_not_require_openai_api_key():
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
