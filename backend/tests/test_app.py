from fastapi.testclient import TestClient
from langchain_core.embeddings import DeterministicFakeEmbedding

from app import main


calls = []


async def fake_stream(graph, request, sources):
    yield "- Writing report\n\n---\n\n# Report\nok"


def fake_graph(app, reasoning_effort):
    calls.append(reasoning_effort)
    return object()


main.init_embeddings = lambda *args, **kwargs: DeterministicFakeEmbedding(size=8)
main.graph_for = fake_graph
main.stream = fake_stream


def test_upload_queues_text_file():
    with TestClient(main.app) as client:
        response = client.post("/api/sources", files=[("files", ("notes.txt", b"hello", "text/plain"))])
        assert response.status_code == 200
        assert response.json()["status"] == "queued"


def test_research_streams_markdown():
    calls.clear()
    with TestClient(main.app) as client:
        response = client.post("/api/research", json={"request": "research this", "reasoning_effort": "low"})
        assert response.status_code == 200
        assert "# Report\nok" in response.text
        assert calls[-1] == "low"


def test_rejects_bad_input():
    with TestClient(main.app) as client:
        assert client.post("/api/research", json={"request": " "}).status_code == 422
        assert client.post("/api/sources", files=[("files", ("empty.txt", b"", "text/plain"))]).status_code == 400
