# tests/unit/notes/services/test_gcs_service.py

import pytest
from unittest.mock import MagicMock, patch, call
from fastapi import HTTPException


BUCKET_NAME = "test-bucket"
FILENAME = "lecture.pdf"
CONTENT_TYPE = "application/pdf"
FILE_CONTENT = b"PDF bytes"
BLOB_NAME = "uploads/20260401_120000_abcd1234_lecture.pdf"
PUBLIC_URL = f"https://storage.googleapis.com/{BUCKET_NAME}/{BLOB_NAME}"


def _make_mock_file(filename=FILENAME, content_type=CONTENT_TYPE):
    f = MagicMock()
    f.filename = filename
    f.content_type = content_type
    f.file = MagicMock()
    f.file.read.return_value = FILE_CONTENT
    return f


def _make_mock_client(bucket_name=BUCKET_NAME):
    blob = MagicMock()
    blob.exists.return_value = True
    blob.generate_signed_url.return_value = "https://signed.url/token"

    bucket = MagicMock()
    bucket.blob.return_value = blob

    client = MagicMock()
    client.bucket.return_value = bucket

    return client, bucket, blob


# ══════════════════════════════════════════════════════════════════════════════
# get_gcs_client
# ══════════════════════════════════════════════════════════════════════════════
class TestGetGCSClient:

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        import Notes.services.gcs_service as svc
        svc._client = None
        svc._credentials = None
        svc._project_id = None
        yield
        svc._client = None

    @patch("Notes.services.gcs_service.gauth_default")
    @patch("Notes.services.gcs_service.storage.Client")
    def test_returns_client_on_success(self, MockClient, mock_auth):
        mock_auth.return_value = (MagicMock(), "test-project")
        mock_instance = MagicMock()
        mock_instance.list_buckets.return_value = []
        MockClient.return_value = mock_instance

        from Notes.services.gcs_service import get_gcs_client
        client = get_gcs_client()
        assert client is mock_instance

    @patch("Notes.services.gcs_service.gauth_default")
    @patch("Notes.services.gcs_service.storage.Client")
    def test_singleton_returns_same_instance(self, MockClient, mock_auth):
        mock_auth.return_value = (MagicMock(), "test-project")
        mock_instance = MagicMock()
        mock_instance.list_buckets.return_value = []
        MockClient.return_value = mock_instance

        from Notes.services.gcs_service import get_gcs_client
        c1 = get_gcs_client()
        c2 = get_gcs_client()

        assert c1 is c2
        MockClient.assert_called_once()

    @patch("Notes.services.gcs_service.gauth_default")
    def test_auth_failure_raises_exception(self, mock_auth):
        mock_auth.side_effect = Exception("No credentials found")

        import Notes.services.gcs_service as svc
        svc._client = None

        from Notes.services.gcs_service import get_gcs_client
        with pytest.raises(Exception, match="No credentials found"):
            get_gcs_client()

    @patch("Notes.services.gcs_service.gauth_default")
    @patch("Notes.services.gcs_service.storage.Client")
    def test_client_set_to_none_on_failure(self, MockClient, mock_auth):
        mock_auth.side_effect = RuntimeError("auth error")

        import Notes.services.gcs_service as svc
        svc._client = None

        from Notes.services.gcs_service import get_gcs_client
        with pytest.raises(RuntimeError):
            get_gcs_client()

        assert svc._client is None

    @patch("Notes.services.gcs_service.gauth_default")
    @patch("Notes.services.gcs_service.storage.Client")
    def test_storage_client_constructed_with_credentials(self, MockClient, mock_auth):
        creds = MagicMock()
        mock_auth.return_value = (creds, "my-project")
        mock_instance = MagicMock()
        mock_instance.list_buckets.return_value = []
        MockClient.return_value = mock_instance

        from Notes.services.gcs_service import get_gcs_client
        get_gcs_client()

        MockClient.assert_called_once_with(credentials=creds, project="my-project")


# ══════════════════════════════════════════════════════════════════════════════
# upload_file_to_gcs
# ══════════════════════════════════════════════════════════════════════════════
class TestUploadFileToGCS:

    @pytest.fixture(autouse=True)
    def patch_bucket_name(self, monkeypatch):
        monkeypatch.setenv("GCS_BUCKET", BUCKET_NAME)
        import Notes.services.gcs_service as svc
        svc.BUCKET_NAME = BUCKET_NAME

    def test_returns_public_url_string(self):
        client, bucket, blob = _make_mock_client()
        from Notes.services.gcs_service import upload_file_to_gcs
        url = upload_file_to_gcs(_make_mock_file(), FILE_CONTENT, client=client)
        assert url.startswith("https://storage.googleapis.com/")

    def test_url_contains_bucket_name(self):
        client, _, _ = _make_mock_client()
        from Notes.services.gcs_service import upload_file_to_gcs
        url = upload_file_to_gcs(_make_mock_file(), FILE_CONTENT, client=client)
        assert BUCKET_NAME in url

    def test_url_contains_filename(self):
        client, _, _ = _make_mock_client()
        from Notes.services.gcs_service import upload_file_to_gcs
        url = upload_file_to_gcs(_make_mock_file(), FILE_CONTENT, client=client)
        assert FILENAME.replace(" ", "_") in url

    def test_blob_name_prefixed_with_uploads(self):
        client, bucket, _ = _make_mock_client()
        from Notes.services.gcs_service import upload_file_to_gcs
        upload_file_to_gcs(_make_mock_file(), FILE_CONTENT, client=client)
        blob_name_used = bucket.blob.call_args[0][0]
        assert blob_name_used.startswith("uploads/")

    def test_upload_from_string_called_with_content(self):
        client, _, blob = _make_mock_client()
        from Notes.services.gcs_service import upload_file_to_gcs
        upload_file_to_gcs(_make_mock_file(), FILE_CONTENT, client=client)
        blob.upload_from_string.assert_called_once_with(FILE_CONTENT, content_type=CONTENT_TYPE)

    def test_upload_from_string_uses_file_read_when_no_content(self):
        client, _, blob = _make_mock_client()
        mock_file = _make_mock_file()
        mock_file.file.read.return_value = b"read bytes"

        from Notes.services.gcs_service import upload_file_to_gcs
        upload_file_to_gcs(mock_file, file_content=None, client=client)

        blob.upload_from_string.assert_called_once_with(b"read bytes", content_type=CONTENT_TYPE)

    def test_spaces_in_filename_replaced_with_underscores(self):
        client, bucket, _ = _make_mock_client()
        file = _make_mock_file(filename="my lecture notes.pdf")

        from Notes.services.gcs_service import upload_file_to_gcs
        upload_file_to_gcs(file, FILE_CONTENT, client=client)

        blob_name_used = bucket.blob.call_args[0][0]
        assert " " not in blob_name_used
        assert "my_lecture_notes.pdf" in blob_name_used

    def test_slashes_in_filename_replaced_with_underscores(self):
        client, bucket, _ = _make_mock_client()
        file = _make_mock_file(filename="folder/sub/file.pdf")

        from Notes.services.gcs_service import upload_file_to_gcs
        upload_file_to_gcs(file, FILE_CONTENT, client=client)

        blob_name_used = bucket.blob.call_args[0][0]
        assert "folder_sub_file.pdf" in blob_name_used

    def test_blob_name_includes_timestamp_and_uuid(self):
        client, bucket, _ = _make_mock_client()

        from Notes.services.gcs_service import upload_file_to_gcs
        upload_file_to_gcs(_make_mock_file(), FILE_CONTENT, client=client)

        blob_name_used = bucket.blob.call_args[0][0]
        parts = blob_name_used.split("/")[1].split("_")
        # format: uploads/YYYYMMDD_HHMMSS_uuid8_filename
        assert len(parts[0]) == 8   # YYYYMMDD
        assert len(parts[1]) == 6   # HHMMSS
        assert len(parts[2]) == 8   # uuid[:8]

    def test_upload_exception_raises_http_500(self):
        client, _, blob = _make_mock_client()
        blob.upload_from_string.side_effect = RuntimeError("quota exceeded")

        from Notes.services.gcs_service import upload_file_to_gcs
        with pytest.raises(HTTPException) as exc:
            upload_file_to_gcs(_make_mock_file(), FILE_CONTENT, client=client)
        assert exc.value.status_code == 500
        assert "File upload failed" in exc.value.detail

    def test_none_client_falls_back_to_singleton(self):
        fallback_client, _, blob = _make_mock_client()

        with patch("Notes.services.gcs_service.get_gcs_client", return_value=fallback_client):
            from Notes.services.gcs_service import upload_file_to_gcs
            url = upload_file_to_gcs(_make_mock_file(), FILE_CONTENT, client=None)

        assert url.startswith("https://storage.googleapis.com/")


# ══════════════════════════════════════════════════════════════════════════════
# delete_file_from_gcs
# ══════════════════════════════════════════════════════════════════════════════
class TestDeleteFileFromGCS:

    @pytest.fixture(autouse=True)
    def patch_bucket_name(self, monkeypatch):
        import Notes.services.gcs_service as svc
        svc.BUCKET_NAME = BUCKET_NAME

    def _url(self, blob_name=BLOB_NAME):
        return f"https://storage.googleapis.com/{BUCKET_NAME}/{blob_name}"

    def test_returns_true_when_blob_exists_and_deleted(self):
        client, _, blob = _make_mock_client()
        blob.exists.return_value = True

        from Notes.services.gcs_service import delete_file_from_gcs
        result = delete_file_from_gcs(self._url(), client=client)
        assert result is True

    def test_blob_delete_called_when_exists(self):
        client, _, blob = _make_mock_client()
        blob.exists.return_value = True

        from Notes.services.gcs_service import delete_file_from_gcs
        delete_file_from_gcs(self._url(), client=client)
        blob.delete.assert_called_once()

    def test_returns_false_when_blob_not_found(self):
        client, _, blob = _make_mock_client()
        blob.exists.return_value = False

        from Notes.services.gcs_service import delete_file_from_gcs
        result = delete_file_from_gcs(self._url(), client=client)
        assert result is False

    def test_delete_not_called_when_blob_not_found(self):
        client, _, blob = _make_mock_client()
        blob.exists.return_value = False

        from Notes.services.gcs_service import delete_file_from_gcs
        delete_file_from_gcs(self._url(), client=client)
        blob.delete.assert_not_called()

    def test_returns_false_for_invalid_url(self):
        client, _, _ = _make_mock_client()

        from Notes.services.gcs_service import delete_file_from_gcs
        result = delete_file_from_gcs("https://other-bucket.com/file.pdf", client=client)
        assert result is False

    def test_blob_name_extracted_correctly_from_url(self):
        client, bucket, blob = _make_mock_client()
        blob.exists.return_value = True

        from Notes.services.gcs_service import delete_file_from_gcs
        delete_file_from_gcs(self._url(BLOB_NAME), client=client)

        bucket.blob.assert_called_once_with(BLOB_NAME)

    def test_exception_returns_false(self):
        client, _, blob = _make_mock_client()
        blob.exists.side_effect = RuntimeError("GCS error")

        from Notes.services.gcs_service import delete_file_from_gcs
        result = delete_file_from_gcs(self._url(), client=client)
        assert result is False

    def test_none_client_falls_back_to_singleton(self):
        fallback_client, _, blob = _make_mock_client()
        blob.exists.return_value = True

        with patch("Notes.services.gcs_service.get_gcs_client", return_value=fallback_client):
            from Notes.services.gcs_service import delete_file_from_gcs
            result = delete_file_from_gcs(self._url(), client=None)

        assert result is True


# ══════════════════════════════════════════════════════════════════════════════
# get_signed_url
# ══════════════════════════════════════════════════════════════════════════════
class TestGetSignedURL:

    @pytest.fixture(autouse=True)
    def patch_bucket_name(self, monkeypatch):
        import Notes.services.gcs_service as svc
        svc.BUCKET_NAME = BUCKET_NAME

    def _url(self, blob_name=BLOB_NAME):
        return f"https://storage.googleapis.com/{BUCKET_NAME}/{blob_name}"

    def test_returns_signed_url_string(self):
        client, _, blob = _make_mock_client()

        from Notes.services.gcs_service import get_signed_url
        url = get_signed_url(self._url(), client=client)
        assert url == "https://signed.url/token"

    def test_signed_url_uses_v4(self):
        client, _, blob = _make_mock_client()

        from Notes.services.gcs_service import get_signed_url
        get_signed_url(self._url(), client=client)

        call_kwargs = blob.generate_signed_url.call_args.kwargs
        assert call_kwargs["version"] == "v4"

    def test_signed_url_method_is_get(self):
        client, _, blob = _make_mock_client()

        from Notes.services.gcs_service import get_signed_url
        get_signed_url(self._url(), client=client)

        call_kwargs = blob.generate_signed_url.call_args.kwargs
        assert call_kwargs["method"] == "GET"

    def test_default_expiration_is_60_minutes(self):
        from datetime import timedelta
        client, _, blob = _make_mock_client()

        from Notes.services.gcs_service import get_signed_url
        get_signed_url(self._url(), client=client)

        call_kwargs = blob.generate_signed_url.call_args.kwargs
        assert call_kwargs["expiration"] == timedelta(minutes=60)

    def test_custom_expiration_passed_correctly(self):
        from datetime import timedelta
        client, _, blob = _make_mock_client()

        from Notes.services.gcs_service import get_signed_url
        get_signed_url(self._url(), expiration_minutes=30, client=client)

        call_kwargs = blob.generate_signed_url.call_args.kwargs
        assert call_kwargs["expiration"] == timedelta(minutes=30)

    def test_blob_name_extracted_from_url(self):
        client, bucket, _ = _make_mock_client()

        from Notes.services.gcs_service import get_signed_url
        get_signed_url(self._url(BLOB_NAME), client=client)

        bucket.blob.assert_called_once_with(BLOB_NAME)

    def test_invalid_url_returns_none(self):
        client, _, _ = _make_mock_client()

        from Notes.services.gcs_service import get_signed_url
        result = get_signed_url("https://other-service.com/file.pdf", client=client)
        assert result is None

    def test_exception_returns_none(self):
        client, _, blob = _make_mock_client()
        blob.generate_signed_url.side_effect = RuntimeError("signing failed")

        from Notes.services.gcs_service import get_signed_url
        result = get_signed_url(self._url(), client=client)
        assert result is None

    def test_none_client_falls_back_to_singleton(self):
        fallback_client, _, blob = _make_mock_client()

        with patch("Notes.services.gcs_service.get_gcs_client", return_value=fallback_client):
            from Notes.services.gcs_service import get_signed_url
            url = get_signed_url(self._url(), client=None)

        assert url == "https://signed.url/token"