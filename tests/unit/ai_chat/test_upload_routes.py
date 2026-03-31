# tests/unit/ai_chat/test_upload_routes.py

import pytest
import numpy as np
from unittest.mock import MagicMock, patch
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport


@pytest.fixture
def client():
    from ai_chat.app.routes.upload import router

    app = FastAPI()
    app.include_router(router, prefix="/upload")
    return app


# ─────────────────────────────────────────────
# POST /upload
# ─────────────────────────────────────────────

class TestUploadDocuments:

    @patch("ai_chat.app.routes.upload.get_faiss_store")
    @patch("ai_chat.app.routes.upload.embed_texts")
    @patch("ai_chat.app.routes.upload.chunk_text")
    @patch("ai_chat.app.routes.upload.extract_text")
    @pytest.mark.anyio
    async def test_upload_single_file_returns_200(
        self, mock_extract, mock_chunk, mock_embed, mock_faiss, client
    ):
        mock_extract.return_value = "Sample document text."
        mock_chunk.return_value = ["chunk one", "chunk two"]
        mock_embed.return_value = np.zeros((2, 384))
        mock_store = MagicMock()
        mock_faiss.return_value = mock_store

        async with AsyncClient(
            transport=ASGITransport(app=client), base_url="http://test"
        ) as ac:
            response = await ac.post(
                "/upload",
                files=[("files", ("doc.pdf", b"fake pdf content", "application/pdf"))],
            )

        assert response.status_code == 200
        data = response.json()
        assert data["files_processed"] == 1
        assert data["total_chunks_added"] == 2

    @patch("ai_chat.app.routes.upload.get_faiss_store")
    @patch("ai_chat.app.routes.upload.embed_texts")
    @patch("ai_chat.app.routes.upload.chunk_text")
    @patch("ai_chat.app.routes.upload.extract_text")
    @pytest.mark.anyio
    async def test_upload_multiple_files(
        self, mock_extract, mock_chunk, mock_embed, mock_faiss, client
    ):
        mock_extract.return_value = "Some text content."
        mock_chunk.return_value = ["chunk a", "chunk b", "chunk c"]
        mock_embed.return_value = np.zeros((3, 384))
        mock_faiss.return_value = MagicMock()

        async with AsyncClient(
            transport=ASGITransport(app=client), base_url="http://test"
        ) as ac:
            response = await ac.post(
                "/upload",
                files=[
                    ("files", ("file1.pdf", b"content1", "application/pdf")),
                    ("files", ("file2.txt", b"content2", "text/plain")),
                ],
            )

        assert response.status_code == 200
        data = response.json()
        assert data["files_processed"] == 2
        assert data["total_chunks_added"] == 6  # 3 chunks × 2 files

    @patch("ai_chat.app.routes.upload.get_faiss_store")
    @patch("ai_chat.app.routes.upload.embed_texts")
    @patch("ai_chat.app.routes.upload.chunk_text")
    @patch("ai_chat.app.routes.upload.extract_text")
    @pytest.mark.anyio
    async def test_upload_response_has_message_field(
        self, mock_extract, mock_chunk, mock_embed, mock_faiss, client
    ):
        mock_extract.return_value = "Text."
        mock_chunk.return_value = ["chunk"]
        mock_embed.return_value = np.zeros((1, 384))
        mock_faiss.return_value = MagicMock()

        async with AsyncClient(
            transport=ASGITransport(app=client), base_url="http://test"
        ) as ac:
            response = await ac.post(
                "/upload",
                files=[("files", ("test.pdf", b"bytes", "application/pdf"))],
            )

        assert "message" in response.json()
        assert "1" in response.json()["message"]

    @patch("ai_chat.app.routes.upload.extract_text")
    @pytest.mark.anyio
    async def test_upload_empty_text_skips_file(self, mock_extract, client):
        """Files that extract to empty string are silently skipped."""
        mock_extract.return_value = "   "  # whitespace only

        async with AsyncClient(
            transport=ASGITransport(app=client), base_url="http://test"
        ) as ac:
            response = await ac.post(
                "/upload",
                files=[("files", ("empty.pdf", b"no text", "application/pdf"))],
            )

        assert response.status_code == 200
        assert response.json()["files_processed"] == 0
        assert response.json()["total_chunks_added"] == 0

    @patch("ai_chat.app.routes.upload.chunk_text")
    @patch("ai_chat.app.routes.upload.extract_text")
    @pytest.mark.anyio
    async def test_upload_empty_chunks_skips_file(
        self, mock_extract, mock_chunk, client
    ):
        """Files that produce no chunks after splitting are skipped."""
        mock_extract.return_value = "Some text."
        mock_chunk.return_value = []  # chunker returns nothing

        async with AsyncClient(
            transport=ASGITransport(app=client), base_url="http://test"
        ) as ac:
            response = await ac.post(
                "/upload",
                files=[("files", ("sparse.pdf", b"data", "application/pdf"))],
            )

        assert response.status_code == 200
        assert response.json()["files_processed"] == 0

    @patch("ai_chat.app.routes.upload.extract_text")
    @pytest.mark.anyio
    async def test_upload_extract_error_returns_400(self, mock_extract, client):
        """An exception during extraction raises HTTP 400."""
        mock_extract.side_effect = ValueError("Unsupported file type")

        async with AsyncClient(
            transport=ASGITransport(app=client), base_url="http://test"
        ) as ac:
            response = await ac.post(
                "/upload",
                files=[("files", ("bad.xyz", b"garbage", "application/octet-stream"))],
            )

        assert response.status_code == 400
        assert "bad.xyz" in response.json()["detail"]

    @patch("ai_chat.app.routes.upload.get_faiss_store")
    @patch("ai_chat.app.routes.upload.embed_texts")
    @patch("ai_chat.app.routes.upload.chunk_text")
    @patch("ai_chat.app.routes.upload.extract_text")
    @pytest.mark.anyio
    async def test_faiss_add_documents_called_with_correct_args(
        self, mock_extract, mock_chunk, mock_embed, mock_faiss, client
    ):
        mock_extract.return_value = "Content."
        mock_chunk.return_value = ["chunk1"]
        embeddings = np.zeros((1, 384))
        mock_embed.return_value = embeddings
        mock_store = MagicMock()
        mock_faiss.return_value = mock_store

        async with AsyncClient(
            transport=ASGITransport(app=client), base_url="http://test"
        ) as ac:
            await ac.post(
                "/upload",
                files=[("files", ("notes.txt", b"text", "text/plain"))],
            )

        mock_store.add_documents.assert_called_once_with(
            embeddings, ["chunk1"], "notes.txt"
        )

    @patch("ai_chat.app.routes.upload.get_faiss_store")
    @patch("ai_chat.app.routes.upload.embed_texts")
    @patch("ai_chat.app.routes.upload.chunk_text")
    @patch("ai_chat.app.routes.upload.extract_text")
    @pytest.mark.anyio
    async def test_faiss_store_initialized_with_embedding_dimension(
        self, mock_extract, mock_chunk, mock_embed, mock_faiss, client
    ):
        mock_extract.return_value = "Text."
        mock_chunk.return_value = ["chunk"]
        mock_embed.return_value = np.zeros((1, 768))  # 768-dim embeddings
        mock_faiss.return_value = MagicMock()

        async with AsyncClient(
            transport=ASGITransport(app=client), base_url="http://test"
        ) as ac:
            await ac.post(
                "/upload",
                files=[("files", ("doc.pdf", b"data", "application/pdf"))],
            )

        mock_faiss.assert_called_once_with(dimension=768)


# ─────────────────────────────────────────────
# GET /upload/stats
# ─────────────────────────────────────────────

class TestUploadStats:

    @patch("ai_chat.app.routes.upload.get_faiss_store")
    @pytest.mark.anyio
    async def test_stats_returns_200(self, mock_faiss, client):
        mock_store = MagicMock()
        mock_store.get_stats.return_value = {"total_documents": 10, "total_chunks": 42}
        mock_faiss.return_value = mock_store

        async with AsyncClient(
            transport=ASGITransport(app=client), base_url="http://test"
        ) as ac:
            response = await ac.get("/upload/stats")

        assert response.status_code == 200

    @patch("ai_chat.app.routes.upload.get_faiss_store")
    @pytest.mark.anyio
    async def test_stats_returns_faiss_store_stats(self, mock_faiss, client):
        mock_store = MagicMock()
        mock_store.get_stats.return_value = {"total_documents": 5, "total_chunks": 20}
        mock_faiss.return_value = mock_store

        async with AsyncClient(
            transport=ASGITransport(app=client), base_url="http://test"
        ) as ac:
            response = await ac.get("/upload/stats")

        data = response.json()
        assert data["total_documents"] == 5
        assert data["total_chunks"] == 20

    @patch("ai_chat.app.routes.upload.get_faiss_store")
    @pytest.mark.anyio
    async def test_stats_calls_get_stats_on_store(self, mock_faiss, client):
        mock_store = MagicMock()
        mock_store.get_stats.return_value = {}
        mock_faiss.return_value = mock_store

        async with AsyncClient(
            transport=ASGITransport(app=client), base_url="http://test"
        ) as ac:
            await ac.get("/upload/stats")

        mock_store.get_stats.assert_called_once()

    @patch("ai_chat.app.routes.upload.get_faiss_store")
    @pytest.mark.anyio
    async def test_stats_empty_store(self, mock_faiss, client):
        mock_store = MagicMock()
        mock_store.get_stats.return_value = {"total_documents": 0, "total_chunks": 0}
        mock_faiss.return_value = mock_store

        async with AsyncClient(
            transport=ASGITransport(app=client), base_url="http://test"
        ) as ac:
            response = await ac.get("/upload/stats")

        assert response.json()["total_documents"] == 0