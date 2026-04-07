# tests/unit/notes/routes/test_notes_sources.py

import pytest
import io
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from fastapi import FastAPI
from fastapi.testclient import TestClient

USER_ID = "user_abc"
NOTEBOOK_ID = uuid4()
SOURCE_ID = uuid4()


def make_mock_notebook():
    nb = MagicMock()
    nb.id = NOTEBOOK_ID
    nb.user_id = USER_ID
    nb.title = "Test Notebook"
    return nb


def make_mock_source(type="file"):
    src = MagicMock()
    src.id = SOURCE_ID
    src.notebook_id = NOTEBOOK_ID
    src.type = type
    src.filename = "test.pdf"
    src.file_url = "https://storage.example.com/test.pdf"
    src.website_url = None
    src.youtube_url = None
    src.extracted_text = "Sample extracted text content here for testing purposes."
    src.source_metadata = {}
    src.created_at = "2026-04-01T00:00:00"
    src.notebook = make_mock_notebook()
    return src


def make_app():
    from Notes.routes.sources import router
    from Notes.utils.auth import get_current_user
    from Notes.db import get_session

    app = FastAPI()
    app.include_router(router)

    mock_user = MagicMock()
    mock_user.user_id = USER_ID

    mock_session = AsyncMock()

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: mock_session

    return app, mock_session


def mock_notebook_found(session, notebook=None):
    nb = notebook or make_mock_notebook()
    result = MagicMock()
    result.scalar_one_or_none.return_value = nb
    session.execute = AsyncMock(return_value=result)
    return nb


def mock_notebook_not_found(session):
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    session.execute = AsyncMock(return_value=result)


# ══════════════════════════════════════════════════════════════════════════════
# POST /  — add_source
# ══════════════════════════════════════════════════════════════════════════════
class TestAddSource:

    @pytest.fixture(autouse=True)
    def setup(self):
        self.app, self.session = make_app()
        self.client = TestClient(self.app)
        self.url = "/"

    # ── file type ──────────────────────────────────────────────────────────────

    @patch("routes.sources.store_embeddings_for_source", new_callable=AsyncMock)
    @patch("routes.sources.extract_text_from_file_content")
    @patch("routes.sources.upload_file_to_gcs")
    @patch("routes.sources.get_gcs_client")
    @patch("routes.sources.Source")
    def test_file_upload_returns_201(
        self, MockSource, mock_gcs_client, mock_upload, mock_extract, mock_embed
    ):
        mock_notebook_found(self.session)
        self.session.commit = AsyncMock()
        self.session.refresh = AsyncMock()
        self.session.add = MagicMock()

        src = make_mock_source("file")
        MockSource.return_value = src
        mock_upload.return_value = "https://gcs.example.com/test.pdf"
        mock_extract.return_value = ("Extracted text " * 10, {})
        mock_embed.return_value = [MagicMock()]

        resp = self.client.post(
            self.url,
            data={"notebook_id": str(NOTEBOOK_ID), "type": "file"},
            files={"file": ("test.pdf", b"PDF content here", "application/pdf")},
        )
        assert resp.status_code == 201

    @patch("routes.sources.store_embeddings_for_source", new_callable=AsyncMock)
    @patch("routes.sources.extract_text_from_file_content")
    @patch("routes.sources.upload_file_to_gcs")
    @patch("routes.sources.get_gcs_client")
    @patch("routes.sources.Source")
    def test_file_upload_response_has_id(
        self, MockSource, mock_gcs_client, mock_upload, mock_extract, mock_embed
    ):
        mock_notebook_found(self.session)
        self.session.commit = AsyncMock()
        self.session.refresh = AsyncMock()
        self.session.add = MagicMock()

        src = make_mock_source("file")
        MockSource.return_value = src
        mock_upload.return_value = "https://gcs.example.com/test.pdf"
        mock_extract.return_value = ("Extracted text " * 10, {})
        mock_embed.return_value = [MagicMock()]

        resp = self.client.post(
            self.url,
            data={"notebook_id": str(NOTEBOOK_ID), "type": "file"},
            files={"file": ("test.pdf", b"PDF content here", "application/pdf")},
        )
        assert "id" in resp.json()

    @patch("routes.sources.store_embeddings_for_source", new_callable=AsyncMock)
    @patch("routes.sources.extract_text_from_file_content")
    @patch("routes.sources.upload_file_to_gcs")
    @patch("routes.sources.get_gcs_client")
    @patch("routes.sources.Source")
    def test_embeddings_generated_flag_true_on_success(
        self, MockSource, mock_gcs_client, mock_upload, mock_extract, mock_embed
    ):
        mock_notebook_found(self.session)
        self.session.commit = AsyncMock()
        self.session.refresh = AsyncMock()
        self.session.add = MagicMock()

        src = make_mock_source("file")
        src.extracted_text = "Substantial text content " * 10
        MockSource.return_value = src
        mock_upload.return_value = "https://gcs.example.com/test.pdf"
        mock_extract.return_value = (src.extracted_text, {})
        mock_embed.return_value = [MagicMock(), MagicMock()]

        resp = self.client.post(
            self.url,
            data={"notebook_id": str(NOTEBOOK_ID), "type": "file"},
            files={"file": ("test.pdf", b"PDF content here", "application/pdf")},
        )
        assert resp.json()["embeddings_generated"] is True

    @patch("routes.sources.extract_text_from_file_content")
    @patch("routes.sources.upload_file_to_gcs")
    @patch("routes.sources.get_gcs_client")
    def test_file_type_without_file_returns_400(
        self, mock_gcs_client, mock_upload, mock_extract
    ):
        mock_notebook_found(self.session)
        resp = self.client.post(
            self.url,
            data={"notebook_id": str(NOTEBOOK_ID), "type": "file"},
        )
        assert resp.status_code == 400
        assert "File is required" in resp.json()["detail"]

    @patch("routes.sources.extract_text_from_file_content")
    @patch("routes.sources.upload_file_to_gcs")
    @patch("routes.sources.get_gcs_client")
    def test_empty_file_returns_400(
        self, mock_gcs_client, mock_upload, mock_extract
    ):
        mock_notebook_found(self.session)
        resp = self.client.post(
            self.url,
            data={"notebook_id": str(NOTEBOOK_ID), "type": "file"},
            files={"file": ("empty.pdf", b"", "application/pdf")},
        )
        assert resp.status_code == 400
        assert "empty" in resp.json()["detail"].lower()

    @patch("routes.sources.extract_text_from_file_content")
    @patch("routes.sources.upload_file_to_gcs")
    @patch("routes.sources.get_gcs_client")
    def test_gcs_upload_failure_returns_500(
        self, mock_gcs_client, mock_upload, mock_extract
    ):
        mock_notebook_found(self.session)
        mock_upload.side_effect = RuntimeError("GCS bucket not found")

        resp = self.client.post(
            self.url,
            data={"notebook_id": str(NOTEBOOK_ID), "type": "file"},
            files={"file": ("test.pdf", b"PDF content", "application/pdf")},
        )
        assert resp.status_code == 500
        assert "File upload failed" in resp.json()["detail"]

    # ── website type ───────────────────────────────────────────────────────────

    @patch("routes.sources.store_embeddings_for_source", new_callable=AsyncMock)
    @patch("routes.sources.extract_from_url", new_callable=AsyncMock)
    @patch("routes.sources.Source")
    def test_website_type_returns_201(self, MockSource, mock_extract, mock_embed):
        mock_notebook_found(self.session)
        self.session.commit = AsyncMock()
        self.session.refresh = AsyncMock()
        self.session.add = MagicMock()

        src = make_mock_source("website")
        src.website_url = "https://example.com"
        MockSource.return_value = src
        mock_extract.return_value = ("Website content " * 10, {"title": "Example"})
        mock_embed.return_value = []

        resp = self.client.post(
            self.url,
            data={
                "notebook_id": str(NOTEBOOK_ID),
                "type": "website",
                "website_url": "https://example.com",
            },
        )
        assert resp.status_code == 201

    @patch("routes.sources.extract_from_url", new_callable=AsyncMock)
    def test_website_type_without_url_returns_400(self, mock_extract):
        mock_notebook_found(self.session)
        resp = self.client.post(
            self.url,
            data={"notebook_id": str(NOTEBOOK_ID), "type": "website"},
        )
        assert resp.status_code == 400
        assert "Website URL is required" in resp.json()["detail"]

    @patch("routes.sources.store_embeddings_for_source", new_callable=AsyncMock)
    @patch("routes.sources.extract_from_url", new_callable=AsyncMock)
    @patch("routes.sources.Source")
    def test_website_extraction_failure_still_creates_source(
        self, MockSource, mock_extract, mock_embed
    ):
        mock_notebook_found(self.session)
        self.session.commit = AsyncMock()
        self.session.refresh = AsyncMock()
        self.session.add = MagicMock()

        src = make_mock_source("website")
        MockSource.return_value = src
        mock_extract.side_effect = RuntimeError("Connection refused")
        mock_embed.return_value = []

        resp = self.client.post(
            self.url,
            data={
                "notebook_id": str(NOTEBOOK_ID),
                "type": "website",
                "website_url": "https://example.com",
            },
        )
        # Source should still be created even if extraction fails
        assert resp.status_code == 201

    # ── youtube type ───────────────────────────────────────────────────────────

    @patch("routes.sources.store_embeddings_for_source", new_callable=AsyncMock)
    @patch("routes.sources.extract_from_youtube", new_callable=AsyncMock)
    @patch("routes.sources.Source")
    def test_youtube_type_returns_201(self, MockSource, mock_extract, mock_embed):
        mock_notebook_found(self.session)
        self.session.commit = AsyncMock()
        self.session.refresh = AsyncMock()
        self.session.add = MagicMock()

        src = make_mock_source("youtube")
        src.youtube_url = "https://youtube.com/watch?v=abc"
        MockSource.return_value = src
        mock_extract.return_value = ("Transcript content " * 10, {"title": "Video"})
        mock_embed.return_value = []

        resp = self.client.post(
            self.url,
            data={
                "notebook_id": str(NOTEBOOK_ID),
                "type": "youtube",
                "youtube_url": "https://youtube.com/watch?v=abc",
            },
        )
        assert resp.status_code == 201

    @patch("routes.sources.extract_from_youtube", new_callable=AsyncMock)
    def test_youtube_type_without_url_returns_400(self, mock_extract):
        mock_notebook_found(self.session)
        resp = self.client.post(
            self.url,
            data={"notebook_id": str(NOTEBOOK_ID), "type": "youtube"},
        )
        assert resp.status_code == 400
        assert "YouTube URL is required" in resp.json()["detail"]

    # ── invalid type ───────────────────────────────────────────────────────────

    def test_invalid_type_returns_400(self):
        mock_notebook_found(self.session)
        resp = self.client.post(
            self.url,
            data={"notebook_id": str(NOTEBOOK_ID), "type": "audio"},
        )
        assert resp.status_code == 400
        assert "Invalid source type" in resp.json()["detail"]

    # ── notebook checks ────────────────────────────────────────────────────────

    def test_notebook_not_found_returns_404(self):
        mock_notebook_not_found(self.session)
        resp = self.client.post(
            self.url,
            data={"notebook_id": str(NOTEBOOK_ID), "type": "website",
                  "website_url": "https://example.com"},
        )
        assert resp.status_code == 404
        assert "Notebook not found" in resp.json()["detail"]

    # ── extracted text truncation ──────────────────────────────────────────────

    @patch("routes.sources.store_embeddings_for_source", new_callable=AsyncMock)
    @patch("routes.sources.extract_from_url", new_callable=AsyncMock)
    @patch("routes.sources.Source")
    def test_extracted_text_truncated_at_500_in_response(
        self, MockSource, mock_extract, mock_embed
    ):
        mock_notebook_found(self.session)
        self.session.commit = AsyncMock()
        self.session.refresh = AsyncMock()
        self.session.add = MagicMock()

        src = make_mock_source("website")
        src.extracted_text = "A" * 1000
        MockSource.return_value = src
        mock_extract.return_value = (src.extracted_text, {})
        mock_embed.return_value = []

        resp = self.client.post(
            self.url,
            data={"notebook_id": str(NOTEBOOK_ID), "type": "website",
                  "website_url": "https://example.com"},
        )
        text = resp.json()["extracted_text"]
        assert text.endswith("...")
        assert len(text) == 503  # 500 + "..."


# ══════════════════════════════════════════════════════════════════════════════
# GET /{notebook_id}  — get_sources
# ══════════════════════════════════════════════════════════════════════════════
class TestGetSources:

    @pytest.fixture(autouse=True)
    def setup(self):
        self.app, self.session = make_app()
        self.client = TestClient(self.app)
        self.url = f"/{NOTEBOOK_ID}"

    def _mock_notebook_then_sources(self, sources):
        nb_result = MagicMock()
        nb_result.scalar_one_or_none.return_value = make_mock_notebook()

        src_result = MagicMock()
        src_result.scalars.return_value.all.return_value = sources

        self.session.execute = AsyncMock(side_effect=[nb_result, src_result])

    def test_returns_200(self):
        self._mock_notebook_then_sources([make_mock_source()])
        resp = self.client.get(self.url)
        assert resp.status_code == 200

    def test_returns_sources_and_count(self):
        self._mock_notebook_then_sources([make_mock_source(), make_mock_source()])
        resp = self.client.get(self.url)
        data = resp.json()
        assert "sources" in data
        assert data["count"] == 2

    def test_empty_sources_returns_empty_list(self):
        self._mock_notebook_then_sources([])
        resp = self.client.get(self.url)
        assert resp.json()["sources"] == []
        assert resp.json()["count"] == 0

    def test_extracted_text_truncated_at_200(self):
        src = make_mock_source()
        src.extracted_text = "B" * 500
        self._mock_notebook_then_sources([src])
        resp = self.client.get(self.url)
        text = resp.json()["sources"][0]["extracted_text"]
        assert text.endswith("...")
        assert len(text) == 203  # 200 + "..."

    def test_short_extracted_text_not_truncated(self):
        src = make_mock_source()
        src.extracted_text = "Short text."
        self._mock_notebook_then_sources([src])
        resp = self.client.get(self.url)
        assert resp.json()["sources"][0]["extracted_text"] == "Short text."

    def test_notebook_not_found_returns_404(self):
        nb_result = MagicMock()
        nb_result.scalar_one_or_none.return_value = None
        self.session.execute = AsyncMock(return_value=nb_result)
        resp = self.client.get(self.url)
        assert resp.status_code == 404

    def test_invalid_notebook_uuid_returns_422(self):
        resp = self.client.get("/not-a-uuid")
        assert resp.status_code == 422


# ══════════════════════════════════════════════════════════════════════════════
# GET /detail/{source_id}  — get_source_detail
# ══════════════════════════════════════════════════════════════════════════════
class TestGetSourceDetail:

    @pytest.fixture(autouse=True)
    def setup(self):
        self.app, self.session = make_app()
        self.client = TestClient(self.app)
        self.url = f"/detail/{SOURCE_ID}"

    def _mock_source_then_embeddings(self, source, embedding_count=2):
        src_result = MagicMock()
        src_result.scalar_one_or_none.return_value = source

        emb_result = MagicMock()
        emb_result.scalars.return_value.all.return_value = [
            MagicMock() for _ in range(embedding_count)
        ]

        self.session.execute = AsyncMock(side_effect=[src_result, emb_result])

    def test_returns_200(self):
        src = make_mock_source()
        self._mock_source_then_embeddings(src)
        resp = self.client.get(self.url)
        assert resp.status_code == 200

    def test_response_contains_notebook_title(self):
        src = make_mock_source()
        self._mock_source_then_embeddings(src)
        resp = self.client.get(self.url)
        assert "notebook_title" in resp.json()

    def test_response_contains_embeddings_count(self):
        src = make_mock_source()
        self._mock_source_then_embeddings(src, embedding_count=3)
        resp = self.client.get(self.url)
        assert resp.json()["embeddings_count"] == 3

    def test_source_not_found_returns_404(self):
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        self.session.execute = AsyncMock(return_value=result)
        resp = self.client.get(self.url)
        assert resp.status_code == 404

    def test_wrong_user_returns_404(self):
        src = make_mock_source()
        src.notebook.user_id = "other_user"  # different user
        self._mock_source_then_embeddings(src)
        resp = self.client.get(self.url)
        assert resp.status_code == 404

    def test_invalid_source_uuid_returns_422(self):
        resp = self.client.get("/detail/not-a-uuid")
        assert resp.status_code == 422


# ══════════════════════════════════════════════════════════════════════════════
# DELETE /{source_id}  — delete_source
# ══════════════════════════════════════════════════════════════════════════════
class TestDeleteSource:

    @pytest.fixture(autouse=True)
    def setup(self):
        self.app, self.session = make_app()
        self.client = TestClient(self.app)
        self.url = f"/{SOURCE_ID}"

    def _mock_found(self, source=None):
        src = source or make_mock_source()
        result = MagicMock()
        result.scalar_one_or_none.return_value = src
        self.session.execute = AsyncMock(return_value=result)
        self.session.delete = AsyncMock()
        self.session.commit = AsyncMock()
        return src

    def _mock_not_found(self):
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        self.session.execute = AsyncMock(return_value=result)

    def test_returns_200_on_success(self):
        self._mock_found()
        resp = self.client.delete(self.url)
        assert resp.status_code == 200

    def test_returns_success_message(self):
        self._mock_found()
        resp = self.client.delete(self.url)
        assert resp.json()["message"] == "Source deleted successfully"

    def test_session_delete_called(self):
        src = self._mock_found()
        self.client.delete(self.url)
        self.session.delete.assert_called_once_with(src)

    def test_session_commit_called(self):
        self._mock_found()
        self.client.delete(self.url)
        self.session.commit.assert_called_once()

    def test_not_found_returns_404(self):
        self._mock_not_found()
        resp = self.client.delete(self.url)
        assert resp.status_code == 404

    def test_wrong_user_returns_404(self):
        src = make_mock_source()
        src.notebook.user_id = "other_user"
        self._mock_found(src)
        resp = self.client.delete(self.url)
        assert resp.status_code == 404

    def test_session_delete_not_called_when_not_found(self):
        self._mock_not_found()
        self.session.delete = AsyncMock()
        self.client.delete(self.url)
        self.session.delete.assert_not_called()

    def test_invalid_uuid_returns_422(self):
        resp = self.client.delete("/not-a-uuid")
        assert resp.status_code == 422


# ══════════════════════════════════════════════════════════════════════════════
# PATCH /{source_id}  — update_source
# ══════════════════════════════════════════════════════════════════════════════
class TestUpdateSource:

    @pytest.fixture(autouse=True)
    def setup(self):
        self.app, self.session = make_app()
        self.client = TestClient(self.app)

    def _mock_found(self, source_type="website"):
        src = make_mock_source(source_type)
        result = MagicMock()
        result.scalar_one_or_none.return_value = src
        self.session.execute = AsyncMock(return_value=result)
        self.session.commit = AsyncMock()
        self.session.refresh = AsyncMock()
        return src

    def _mock_not_found(self):
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        self.session.execute = AsyncMock(return_value=result)

    def test_update_website_url_returns_200(self):
        self._mock_found("website")
        resp = self.client.patch(
            f"/{SOURCE_ID}",
            data={"website_url": "https://new-url.com"},
        )
        assert resp.status_code == 200

    def test_website_url_updated_on_source(self):
        src = self._mock_found("website")
        self.client.patch(
            f"/{SOURCE_ID}",
            data={"website_url": "https://new-url.com"},
        )
        assert src.website_url == "https://new-url.com"

    def test_update_youtube_url_returns_200(self):
        self._mock_found("youtube")
        resp = self.client.patch(
            f"/{SOURCE_ID}",
            data={"youtube_url": "https://youtube.com/watch?v=xyz"},
        )
        assert resp.status_code == 200

    def test_youtube_url_updated_on_source(self):
        src = self._mock_found("youtube")
        self.client.patch(
            f"/{SOURCE_ID}",
            data={"youtube_url": "https://youtube.com/watch?v=xyz"},
        )
        assert src.youtube_url == "https://youtube.com/watch?v=xyz"

    def test_no_matching_fields_returns_no_update_message(self):
        self._mock_found("file")  # file type — neither website nor youtube
        resp = self.client.patch(
            f"/{SOURCE_ID}",
            data={"website_url": "https://example.com"},
        )
        assert resp.json()["message"] == "No fields to update"

    def test_updated_fields_listed_in_response(self):
        self._mock_found("website")
        resp = self.client.patch(
            f"/{SOURCE_ID}",
            data={"website_url": "https://new-url.com"},
        )
        assert "website_url" in resp.json()["updated_fields"]

    def test_commit_called_when_fields_updated(self):
        self._mock_found("website")
        self.client.patch(
            f"/{SOURCE_ID}",
            data={"website_url": "https://new-url.com"},
        )
        self.session.commit.assert_called_once()

    def test_commit_not_called_when_no_fields_to_update(self):
        self._mock_found("file")
        self.client.patch(
            f"/{SOURCE_ID}",
            data={"website_url": "https://example.com"},
        )
        self.session.commit.assert_not_called()

    def test_source_not_found_returns_404(self):
        self._mock_not_found()
        resp = self.client.patch(
            f"/{SOURCE_ID}",
            data={"website_url": "https://example.com"},
        )
        assert resp.status_code == 404

    def test_wrong_user_returns_404(self):
        src = make_mock_source("website")
        src.notebook.user_id = "other_user"
        result = MagicMock()
        result.scalar_one_or_none.return_value = src
        self.session.execute = AsyncMock(return_value=result)
        resp = self.client.patch(
            f"/{SOURCE_ID}",
            data={"website_url": "https://example.com"},
        )
        assert resp.status_code == 404

    def test_invalid_uuid_returns_422(self):
        resp = self.client.patch("/not-a-uuid", data={"website_url": "https://example.com"})
        assert resp.status_code == 422


# ══════════════════════════════════════════════════════════════════════════════
# Router registration
# ══════════════════════════════════════════════════════════════════════════════
class TestRouterConfig:

    def test_router_has_no_prefix(self):
        from Notes.routes.sources import router
        assert router.prefix == ""

    def test_post_route_registered(self):
        from Notes.routes.sources import router
        paths = [r.path for r in router.routes]
        assert "/" in paths

    def test_get_notebook_sources_route_registered(self):
        from Notes.routes.sources import router
        paths = [r.path for r in router.routes]
        assert "/{notebook_id}" in paths

    def test_get_source_detail_route_registered(self):
        from Notes.routes.sources import router
        paths = [r.path for r in router.routes]
        assert "/detail/{source_id}" in paths

    def test_delete_route_registered(self):
        from Notes.routes.sources import router
        methods = {
            m
            for r in router.routes
            if r.path == "/{source_id}"
            for m in r.methods
        }
        assert "DELETE" in methods

    def test_patch_route_registered(self):
        from Notes.routes.sources import router
        methods = {
            m
            for r in router.routes
            if r.path == "/{source_id}"
            for m in r.methods
        }
        assert "PATCH" in methods