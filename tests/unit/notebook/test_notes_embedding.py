# tests/unit/notes/routes/test_notes_embeddings.py

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi import HTTPException

USER_ID = "user_abc"

MOCK_SEARCH_RESPONSE = {
    "results": [
        {
            "source_id": "src-1",
            "source_name": "notes.pdf",
            "chunk": "Relevant content chunk here.",
            "score": 0.91,
        }
    ],
    "total": 1,
}


def make_app():
    from Notes.routes.embeddings import router
    from Notes.utils.auth import get_current_user
    from Notes.db import get_session

    app = FastAPI()
    app.include_router(router)

    mock_user = MagicMock()
    mock_user.user_id = USER_ID

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()

    return app


# ══════════════════════════════════════════════════════════════════════════════
# POST /semantic-search
# ══════════════════════════════════════════════════════════════════════════════
class TestSearchEmbeddings:

    @pytest.fixture(autouse=True)
    def setup(self):
        self.client = TestClient(make_app())
        self.url = "/semantic-search"
        self.payload = {"query": "What is machine learning?", "notebook_id": "nb-123"}

    # ── happy path ─────────────────────────────────────────────────────────────

    @patch("routes.embeddings.semantic_search", new_callable=AsyncMock)
    def test_returns_200_on_success(self, mock_search):
        mock_search.return_value = MOCK_SEARCH_RESPONSE
        resp = self.client.post(self.url, json=self.payload)
        assert resp.status_code == 200

    @patch("routes.embeddings.semantic_search", new_callable=AsyncMock)
    def test_returns_search_results(self, mock_search):
        mock_search.return_value = MOCK_SEARCH_RESPONSE
        resp = self.client.post(self.url, json=self.payload)
        assert resp.json() == MOCK_SEARCH_RESPONSE

    @patch("routes.embeddings.semantic_search", new_callable=AsyncMock)
    def test_semantic_search_called_once(self, mock_search):
        mock_search.return_value = MOCK_SEARCH_RESPONSE
        self.client.post(self.url, json=self.payload)
        mock_search.assert_called_once()

    @patch("routes.embeddings.semantic_search", new_callable=AsyncMock)
    def test_user_id_passed_to_semantic_search(self, mock_search):
        mock_search.return_value = MOCK_SEARCH_RESPONSE
        self.client.post(self.url, json=self.payload)
        _, _, called_user_id = mock_search.call_args.args
        assert called_user_id == USER_ID

    @patch("routes.embeddings.semantic_search", new_callable=AsyncMock)
    def test_request_data_passed_to_semantic_search(self, mock_search):
        mock_search.return_value = MOCK_SEARCH_RESPONSE
        self.client.post(self.url, json=self.payload)
        called_data = mock_search.call_args.args[0]
        assert called_data.query == self.payload["query"]

    @patch("routes.embeddings.semantic_search", new_callable=AsyncMock)
    def test_session_passed_to_semantic_search(self, mock_search):
        mock_search.return_value = MOCK_SEARCH_RESPONSE
        self.client.post(self.url, json=self.payload)
        called_session = mock_search.call_args.args[1]
        assert called_session is not None

    @patch("routes.embeddings.semantic_search", new_callable=AsyncMock)
    def test_empty_results_returns_200(self, mock_search):
        mock_search.return_value = {"results": [], "total": 0}
        resp = self.client.post(self.url, json=self.payload)
        assert resp.status_code == 200
        assert resp.json()["results"] == []

    # ── error cases ────────────────────────────────────────────────────────────

    @patch("routes.embeddings.semantic_search", new_callable=AsyncMock)
    def test_service_exception_propagates(self, mock_search):
        mock_search.side_effect = HTTPException(status_code=500, detail="Embedding error")
        resp = self.client.post(self.url, json=self.payload)
        assert resp.status_code == 500

    @patch("routes.embeddings.semantic_search", new_callable=AsyncMock)
    def test_service_404_propagates(self, mock_search):
        mock_search.side_effect = HTTPException(status_code=404, detail="Notebook not found")
        resp = self.client.post(self.url, json=self.payload)
        assert resp.status_code == 404
        assert "Notebook not found" in resp.json()["detail"]

    def test_missing_query_returns_422(self):
        resp = self.client.post(self.url, json={"notebook_id": "nb-123"})
        assert resp.status_code == 422

    def test_missing_notebook_id_returns_422(self):
        resp = self.client.post(self.url, json={"query": "some query"})
        assert resp.status_code == 422

    def test_empty_body_returns_422(self):
        resp = self.client.post(self.url, json={})
        assert resp.status_code == 422

    def test_unauthenticated_request_rejected(self):
        from Notes.routes.embeddings import router
        from Notes.db import get_session

        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        # get_current_user NOT overridden — will attempt real auth

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(self.url, json=self.payload)
        assert resp.status_code in (401, 403, 422, 500)


# ══════════════════════════════════════════════════════════════════════════════
# Router registration
# ══════════════════════════════════════════════════════════════════════════════
class TestRouterConfig:

    def test_semantic_search_route_exists(self):
        from Notes.routes.embeddings import router
        paths = [r.path for r in router.routes]
        assert "/semantic-search" in paths

    def test_semantic_search_is_post(self):
        from Notes.routes.embeddings import router
        methods = {
            method
            for r in router.routes
            if r.path == "/semantic-search"
            for method in r.methods
        }
        assert "POST" in methods

    def test_router_has_no_unexpected_prefix(self):
        from Notes.routes.embeddings import router
        assert router.prefix == ""