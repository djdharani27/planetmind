import pytest
from fastapi.testclient import TestClient
from backend.api.main import app

client = TestClient(app)


class TestAPI:
    def test_health_check(self):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["app"] == "PlanetMind AI"

    def test_list_documents_empty_after_startup(self):
        response = client.get("/api/documents")
        assert response.status_code == 200
        data = response.json()
        assert "documents" in data
        assert "total" in data

    def test_upload_rejects_no_file(self):
        response = client.post("/api/documents/upload")
        assert response.status_code == 422

    def test_upload_valid_file(self):
        with open(__file__, "rb") as f:
            response = client.post(
                "/api/documents/upload",
                files={"file": ("test_doc.txt", f, "text/plain")},
            )
        assert response.status_code in (200, 400)

    def test_get_nonexistent_document(self):
        response = client.get("/api/documents/does-not-exist")
        assert response.status_code == 404

    def test_delete_nonexistent_document(self):
        response = client.delete("/api/documents/does-not-exist")
        assert response.status_code == 404

    def test_dashboard(self):
        response = client.get("/api/dashboard")
        assert response.status_code == 200
        data = response.json()
        assert "total_documents" in data
        assert "by_status" in data

    def test_search_empty_query(self):
        response = client.post("/api/search", json={"query": ""})
        assert response.status_code == 200

    def test_chat_empty_question(self):
        response = client.post("/api/chat", json={"question": ""})
        assert response.status_code == 200

    def test_process_invalid_document(self):
        response = client.post("/api/pipeline/process", json={"document_id": "fake-id"})
        assert response.status_code == 404
