"""tests/unit/cs_bot/test_ingestion_service.py"""
import json
import pytest
from unittest.mock import MagicMock, patch


class TestIngestUrls:

    @pytest.mark.asyncio
    async def test_returns_chunk_count(self, mock_vector_store):
        mock_docs = [MagicMock(page_content="text", metadata={"source": "https://a.com"})]
        mock_chunks = [
            MagicMock(page_content="chunk1", metadata={"source": "https://a.com"}),
            MagicMock(page_content="chunk2", metadata={"source": "https://a.com"}),
        ]
        mock_loader = MagicMock()
        mock_loader.load.return_value = mock_docs
        mock_splitter = MagicMock()
        mock_splitter.split_documents.return_value = mock_chunks

        with patch("cs_bot.app.services.ingestion_service.WebBaseLoader", return_value=mock_loader), \
             patch("cs_bot.app.services.ingestion_service.RecursiveCharacterTextSplitter", return_value=mock_splitter), \
             patch("cs_bot.app.services.ingestion_service.get_vector_store", return_value=mock_vector_store):
            from cs_bot.app.services.ingestion_service import ingest_urls
            count = await ingest_urls(["https://a.com"])

        assert count == 2
        mock_vector_store.aadd_documents.assert_called_once_with(mock_chunks)

    @pytest.mark.asyncio
    async def test_preserves_existing_source_metadata(self, mock_vector_store):
        chunk = MagicMock()
        chunk.metadata = {"source": "https://a.com"}
        mock_loader = MagicMock()
        mock_loader.load.return_value = [MagicMock()]
        mock_splitter = MagicMock()
        mock_splitter.split_documents.return_value = [chunk]

        with patch("cs_bot.app.services.ingestion_service.WebBaseLoader", return_value=mock_loader), \
             patch("cs_bot.app.services.ingestion_service.RecursiveCharacterTextSplitter", return_value=mock_splitter), \
             patch("cs_bot.app.services.ingestion_service.get_vector_store", return_value=mock_vector_store):
            from cs_bot.app.services.ingestion_service import ingest_urls
            await ingest_urls(["https://a.com"])

        assert chunk.metadata["source"] == "https://a.com"

    @pytest.mark.asyncio
    async def test_missing_source_defaults_to_empty_string(self, mock_vector_store):
        chunk = MagicMock()
        chunk.metadata = {}
        mock_loader = MagicMock()
        mock_loader.load.return_value = [MagicMock()]
        mock_splitter = MagicMock()
        mock_splitter.split_documents.return_value = [chunk]

        with patch("cs_bot.app.services.ingestion_service.WebBaseLoader", return_value=mock_loader), \
             patch("cs_bot.app.services.ingestion_service.RecursiveCharacterTextSplitter", return_value=mock_splitter), \
             patch("cs_bot.app.services.ingestion_service.get_vector_store", return_value=mock_vector_store):
            from cs_bot.app.services.ingestion_service import ingest_urls
            await ingest_urls(["https://a.com"])

        assert chunk.metadata["source"] == ""

    @pytest.mark.asyncio
    async def test_calls_aadd_documents(self, mock_vector_store):
        mock_loader = MagicMock()
        mock_loader.load.return_value = []
        mock_splitter = MagicMock()
        mock_splitter.split_documents.return_value = []

        with patch("cs_bot.app.services.ingestion_service.WebBaseLoader", return_value=mock_loader), \
             patch("cs_bot.app.services.ingestion_service.RecursiveCharacterTextSplitter", return_value=mock_splitter), \
             patch("cs_bot.app.services.ingestion_service.get_vector_store", return_value=mock_vector_store):
            from cs_bot.app.services.ingestion_service import ingest_urls
            await ingest_urls([])

        mock_vector_store.aadd_documents.assert_called_once()


class TestIngestJson:

    @pytest.mark.asyncio
    async def test_returns_chunk_count(self, mock_vector_store, tmp_path):
        data = [{"content": "Hello world", "page": "https://a.com"}]
        json_file = tmp_path / "website_content.json"
        json_file.write_text(json.dumps(data))

        mock_splitter = MagicMock()
        mock_splitter.split_documents.return_value = [MagicMock(), MagicMock()]

        with patch("cs_bot.app.services.ingestion_service.RecursiveCharacterTextSplitter", return_value=mock_splitter), \
             patch("cs_bot.app.services.ingestion_service.get_vector_store", return_value=mock_vector_store):
            from cs_bot.app.services.ingestion_service import ingest_json
            count = await ingest_json(str(json_file))

        assert count == 2

    @pytest.mark.asyncio
    async def test_creates_documents_with_correct_fields(self, mock_vector_store, tmp_path):
        data = [{"content": "About us", "page": "https://example.com/about"}]
        json_file = tmp_path / "content.json"
        json_file.write_text(json.dumps(data))

        captured = []
        mock_splitter = MagicMock()

        def capture(docs):
            captured.extend(docs)
            return docs

        mock_splitter.split_documents.side_effect = capture

        with patch("cs_bot.app.services.ingestion_service.RecursiveCharacterTextSplitter", return_value=mock_splitter), \
             patch("cs_bot.app.services.ingestion_service.get_vector_store", return_value=mock_vector_store):
            from cs_bot.app.services.ingestion_service import ingest_json
            await ingest_json(str(json_file))

        assert captured[0].metadata["source"] == "https://example.com/about"
        assert captured[0].page_content == "About us"

    @pytest.mark.asyncio
    async def test_multiple_items_all_ingested(self, mock_vector_store, tmp_path):
        data = [
            {"content": "Page A", "page": "https://a.com"},
            {"content": "Page B", "page": "https://b.com"},
        ]
        json_file = tmp_path / "content.json"
        json_file.write_text(json.dumps(data))

        captured = []
        mock_splitter = MagicMock()

        def capture(docs):
            captured.extend(docs)
            return docs

        mock_splitter.split_documents.side_effect = capture

        with patch("cs_bot.app.services.ingestion_service.RecursiveCharacterTextSplitter", return_value=mock_splitter), \
             patch("cs_bot.app.services.ingestion_service.get_vector_store", return_value=mock_vector_store):
            from cs_bot.app.services.ingestion_service import ingest_json
            await ingest_json(str(json_file))

        assert len(captured) == 2
        sources = [d.metadata["source"] for d in captured]
        assert "https://a.com" in sources
        assert "https://b.com" in sources
