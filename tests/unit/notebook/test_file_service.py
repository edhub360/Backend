# tests/unit/notes/services/test_file_service.py

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


GCS_BUCKET = "test-bucket"
FILENAME = "lecture_notes.pdf"
CONTENT_TYPE = "application/pdf"
FILE_CONTENT = b"PDF binary content"
EXPECTED_URL = f"https://storage.googleapis.com/{GCS_BUCKET}/{FILENAME}"


def _make_mock_file(filename=FILENAME, content=FILE_CONTENT, content_type=CONTENT_TYPE):
    f = MagicMock()
    f.filename = filename
    f.content_type = content_type
    f.read = AsyncMock(return_value=content)
    return f


# ══════════════════════════════════════════════════════════════════════════════
# save_file_to_gcs
# ══════════════════════════════════════════════════════════════════════════════
class TestSaveFileToGCS:

    @pytest.fixture(autouse=True)
    def patch_env(self, monkeypatch):
        monkeypatch.setenv("GCS_BUCKET", GCS_BUCKET)

    @pytest.mark.asyncio
    @patch("services.file_service.storage.Client")
    async def test_returns_correct_gcs_url(self, MockClient):
        blob = MagicMock()
        bucket = MagicMock()
        bucket.blob.return_value = blob
        MockClient.return_value.get_bucket.return_value = bucket

        from Notes.services.file_service import save_file_to_gcs
        url = await save_file_to_gcs(_make_mock_file())

        assert url == EXPECTED_URL

    @pytest.mark.asyncio
    @patch("services.file_service.storage.Client")
    async def test_blob_named_after_filename(self, MockClient):
        blob = MagicMock()
        bucket = MagicMock()
        bucket.blob.return_value = blob
        MockClient.return_value.get_bucket.return_value = bucket

        from Notes.services.file_service import save_file_to_gcs
        await save_file_to_gcs(_make_mock_file())

        bucket.blob.assert_called_once_with(FILENAME)

    @pytest.mark.asyncio
    @patch("services.file_service.storage.Client")
    async def test_upload_called_with_file_content(self, MockClient):
        blob = MagicMock()
        bucket = MagicMock()
        bucket.blob.return_value = blob
        MockClient.return_value.get_bucket.return_value = bucket

        from Notes.services.file_service import save_file_to_gcs
        await save_file_to_gcs(_make_mock_file())

        blob.upload_from_string.assert_called_once_with(FILE_CONTENT, CONTENT_TYPE)

    @pytest.mark.asyncio
    @patch("services.file_service.storage.Client")
    async def test_upload_called_with_correct_content_type(self, MockClient):
        blob = MagicMock()
        bucket = MagicMock()
        bucket.blob.return_value = blob
        MockClient.return_value.get_bucket.return_value = bucket

        file = _make_mock_file(content_type="image/png")
        from Notes.services.file_service import save_file_to_gcs
        await save_file_to_gcs(file)

        _, called_content_type = blob.upload_from_string.call_args.args
        assert called_content_type == "image/png"

    @pytest.mark.asyncio
    @patch("services.file_service.storage.Client")
    async def test_file_read_called_once(self, MockClient):
        blob = MagicMock()
        bucket = MagicMock()
        bucket.blob.return_value = blob
        MockClient.return_value.get_bucket.return_value = bucket

        mock_file = _make_mock_file()
        from Notes.services.file_service import save_file_to_gcs
        await save_file_to_gcs(mock_file)

        mock_file.read.assert_called_once()

    @pytest.mark.asyncio
    @patch("services.file_service.storage.Client")
    async def test_get_bucket_called_with_env_bucket_name(self, MockClient):
        blob = MagicMock()
        bucket = MagicMock()
        bucket.blob.return_value = blob
        client_instance = MockClient.return_value
        client_instance.get_bucket.return_value = bucket

        from Notes.services.file_service import save_file_to_gcs
        await save_file_to_gcs(_make_mock_file())

        client_instance.get_bucket.assert_called_once_with(GCS_BUCKET)

    @pytest.mark.asyncio
    @patch("services.file_service.storage.Client")
    async def test_url_contains_bucket_name(self, MockClient):
        blob = MagicMock()
        bucket = MagicMock()
        bucket.blob.return_value = blob
        MockClient.return_value.get_bucket.return_value = bucket

        from Notes.services.file_service import save_file_to_gcs
        url = await save_file_to_gcs(_make_mock_file())

        assert GCS_BUCKET in url

    @pytest.mark.asyncio
    @patch("services.file_service.storage.Client")
    async def test_url_contains_filename(self, MockClient):
        blob = MagicMock()
        bucket = MagicMock()
        bucket.blob.return_value = blob
        MockClient.return_value.get_bucket.return_value = bucket

        from Notes.services.file_service import save_file_to_gcs
        url = await save_file_to_gcs(_make_mock_file())

        assert FILENAME in url

    @pytest.mark.asyncio
    @patch("services.file_service.storage.Client")
    async def test_url_uses_gcs_base_url(self, MockClient):
        blob = MagicMock()
        bucket = MagicMock()
        bucket.blob.return_value = blob
        MockClient.return_value.get_bucket.return_value = bucket

        from Notes.services.file_service import save_file_to_gcs
        url = await save_file_to_gcs(_make_mock_file())

        assert url.startswith("https://storage.googleapis.com/")

    @pytest.mark.asyncio
    @patch("services.file_service.storage.Client")
    async def test_different_filename_reflected_in_url(self, MockClient):
        blob = MagicMock()
        bucket = MagicMock()
        bucket.blob.return_value = blob
        MockClient.return_value.get_bucket.return_value = bucket

        file = _make_mock_file(filename="slides.pptx")
        from Notes.services.file_service import save_file_to_gcs
        url = await save_file_to_gcs(file)

        assert "slides.pptx" in url

    @pytest.mark.asyncio
    @patch("services.file_service.storage.Client")
    async def test_gcs_client_instantiated(self, MockClient):
        blob = MagicMock()
        bucket = MagicMock()
        bucket.blob.return_value = blob
        MockClient.return_value.get_bucket.return_value = bucket

        from Notes.services.file_service import save_file_to_gcs
        await save_file_to_gcs(_make_mock_file())

        MockClient.assert_called_once()

    @pytest.mark.asyncio
    @patch("services.file_service.storage.Client")
    async def test_storage_exception_propagates(self, MockClient):
        MockClient.return_value.get_bucket.side_effect = Exception("Bucket not found")

        from Notes.services.file_service import save_file_to_gcs
        with pytest.raises(Exception, match="Bucket not found"):
            await save_file_to_gcs(_make_mock_file())

    @pytest.mark.asyncio
    @patch("services.file_service.storage.Client")
    async def test_upload_exception_propagates(self, MockClient):
        blob = MagicMock()
        blob.upload_from_string.side_effect = Exception("Upload quota exceeded")
        bucket = MagicMock()
        bucket.blob.return_value = blob
        MockClient.return_value.get_bucket.return_value = bucket

        from Notes.services.file_service import save_file_to_gcs
        with pytest.raises(Exception, match="Upload quota exceeded"):
            await save_file_to_gcs(_make_mock_file())