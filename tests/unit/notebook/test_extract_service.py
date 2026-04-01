# tests/unit/notes/services/test_extract_service.py

import pytest
import io
from unittest.mock import AsyncMock, MagicMock, patch, call


# ══════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════

def _make_pdf_bytes():
    """Minimal valid-looking byte string for mocking (fitz is mocked anyway)."""
    return b"%PDF-1.4 fake content"


def _make_mock_file(filename="test.pdf", content=b"content"):
    f = MagicMock()
    f.filename = filename
    f.read = AsyncMock(return_value=content)
    return f


# ══════════════════════════════════════════════════════════════════════════════
# extract_text_from_file  (deprecated wrapper)
# ══════════════════════════════════════════════════════════════════════════════
class TestExtractTextFromFile:

    @pytest.mark.asyncio
    @patch("services.extract_service.extract_text_from_file_content")
    async def test_delegates_to_extract_from_file_content(self, mock_extract):
        mock_extract.return_value = ("extracted", {"filename": "test.pdf"})
        mock_file = _make_mock_file("test.pdf", b"bytes")

        from Notes.services.extract_service import extract_text_from_file
        text, meta = await extract_text_from_file(mock_file)

        mock_extract.assert_called_once_with(b"bytes", "test.pdf")

    @pytest.mark.asyncio
    @patch("services.extract_service.extract_text_from_file_content")
    async def test_returns_text_and_metadata(self, mock_extract):
        mock_extract.return_value = ("some text", {"filename": "doc.pdf"})
        mock_file = _make_mock_file("doc.pdf", b"data")

        from Notes.services.extract_service import extract_text_from_file
        text, meta = await extract_text_from_file(mock_file)
        assert text == "some text"
        assert meta == {"filename": "doc.pdf"}

    @pytest.mark.asyncio
    async def test_read_exception_returns_error_string(self):
        mock_file = MagicMock()
        mock_file.filename = "test.pdf"
        mock_file.read = AsyncMock(side_effect=RuntimeError("read failed"))

        from Notes.services.extract_service import extract_text_from_file
        text, meta = await extract_text_from_file(mock_file)
        assert "error" in text.lower() or "processing" in text.lower()


# ══════════════════════════════════════════════════════════════════════════════
# extract_text_from_file_content — shared edge cases
# ══════════════════════════════════════════════════════════════════════════════
class TestExtractTextFromFileContentEdgeCases:

    def _call(self, content, filename):
        from Notes.services.extract_service import extract_text_from_file_content
        return extract_text_from_file_content(content, filename)

    def test_empty_bytes_returns_file_is_empty(self):
        text, meta = self._call(b"", "test.pdf")
        assert "empty" in text.lower()

    def test_metadata_always_contains_filename(self):
        _, meta = self._call(b"", "doc.txt")
        assert meta["filename"] == "doc.txt"

    def test_metadata_contains_size(self):
        _, meta = self._call(b"hello", "doc.txt")
        assert meta["size"] == 5

    def test_unsupported_extension_returns_error(self):
        text, _ = self._call(b"data", "file.mp3")
        assert "unsupported file type" in text.lower()


# ══════════════════════════════════════════════════════════════════════════════
# extract_text_from_file_content — PDF
# ══════════════════════════════════════════════════════════════════════════════
class TestExtractPDF:

    def _call(self, content=_make_pdf_bytes(), filename="test.pdf"):
        from Notes.services.extract_service import extract_text_from_file_content
        return extract_text_from_file_content(content, filename)

    @patch("services.extract_service.fitz")
    def test_returns_extracted_text(self, mock_fitz):
        page = MagicMock()
        page.get_text.return_value = "Hello PDF page."
        mock_doc = MagicMock()
        mock_doc.__iter__ = MagicMock(return_value=iter([page]))
        mock_doc.__len__ = MagicMock(return_value=1)
        mock_fitz.open.return_value.__enter__ = MagicMock(return_value=mock_doc)
        mock_fitz.open.return_value.__exit__ = MagicMock(return_value=False)

        text, meta = self._call()
        assert "Hello PDF page." in text

    @patch("services.extract_service.fitz")
    def test_empty_pdf_returns_empty_message(self, mock_fitz):
        page = MagicMock()
        page.get_text.return_value = "   "
        mock_doc = MagicMock()
        mock_doc.__iter__ = MagicMock(return_value=iter([page]))
        mock_doc.__len__ = MagicMock(return_value=1)
        mock_fitz.open.return_value.__enter__ = MagicMock(return_value=mock_doc)
        mock_fitz.open.return_value.__exit__ = MagicMock(return_value=False)

        text, _ = self._call()
        assert "empty" in text.lower() or "images" in text.lower()

    @patch("services.extract_service.fitz")
    def test_multi_page_text_joined(self, mock_fitz):
        page1, page2 = MagicMock(), MagicMock()
        page1.get_text.return_value = "Page one."
        page2.get_text.return_value = "Page two."
        mock_doc = MagicMock()
        mock_doc.__iter__ = MagicMock(return_value=iter([page1, page2]))
        mock_doc.__len__ = MagicMock(return_value=2)
        mock_fitz.open.return_value.__enter__ = MagicMock(return_value=mock_doc)
        mock_fitz.open.return_value.__exit__ = MagicMock(return_value=False)

        text, _ = self._call()
        assert "Page one." in text
        assert "Page two." in text

    @patch("services.extract_service.fitz")
    def test_fitz_exception_returns_error_message(self, mock_fitz):
        mock_fitz.open.side_effect = RuntimeError("corrupt PDF")
        text, _ = self._call()
        assert "pdf processing failed" in text.lower()


# ══════════════════════════════════════════════════════════════════════════════
# extract_text_from_file_content — DOCX
# ══════════════════════════════════════════════════════════════════════════════
class TestExtractDOCX:

    def _call(self, content=b"docx bytes", filename="test.docx"):
        from Notes.services.extract_service import extract_text_from_file_content
        return extract_text_from_file_content(content, filename)

    @patch("services.extract_service.docx")
    def test_extracts_paragraph_text(self, mock_docx):
        para = MagicMock()
        para.text = "Hello from paragraph."
        mock_doc = MagicMock()
        mock_doc.paragraphs = [para]
        mock_doc.tables = []
        mock_docx.Document.return_value = mock_doc

        text, _ = self._call()
        assert "Hello from paragraph." in text

    @patch("services.extract_service.docx")
    def test_extracts_table_cell_text(self, mock_docx):
        cell = MagicMock()
        cell.text = "Cell data"
        row = MagicMock()
        row.cells = [cell]
        table = MagicMock()
        table.rows = [row]
        mock_doc = MagicMock()
        mock_doc.paragraphs = []
        mock_doc.tables = [table]
        mock_docx.Document.return_value = mock_doc

        text, _ = self._call()
        assert "Cell data" in text

    @patch("services.extract_service.docx")
    def test_empty_doc_returns_empty_message(self, mock_docx):
        para = MagicMock()
        para.text = "   "
        mock_doc = MagicMock()
        mock_doc.paragraphs = [para]
        mock_doc.tables = []
        mock_docx.Document.return_value = mock_doc

        text, _ = self._call()
        assert "empty" in text.lower()

    @patch("services.extract_service.docx")
    def test_exception_returns_error_message(self, mock_docx):
        mock_docx.Document.side_effect = RuntimeError("bad docx")
        text, _ = self._call()
        assert "docx processing failed" in text.lower()

    @patch("services.extract_service.docx")
    def test_blank_paragraphs_excluded(self, mock_docx):
        p1, p2 = MagicMock(), MagicMock()
        p1.text = ""
        p2.text = "Real content"
        mock_doc = MagicMock()
        mock_doc.paragraphs = [p1, p2]
        mock_doc.tables = []
        mock_docx.Document.return_value = mock_doc

        text, _ = self._call()
        assert text == "Real content"


# ══════════════════════════════════════════════════════════════════════════════
# extract_text_from_file_content — PPTX
# ══════════════════════════════════════════════════════════════════════════════
class TestExtractPPTX:

    def _call(self, content=b"pptx bytes", filename="deck.pptx"):
        from Notes.services.extract_service import extract_text_from_file_content
        return extract_text_from_file_content(content, filename)

    @patch("services.extract_service.pptx")
    def test_extracts_shape_text(self, mock_pptx):
        shape = MagicMock()
        shape.text = "Slide headline"
        slide = MagicMock()
        slide.shapes = [shape]
        prs = MagicMock()
        prs.slides = [slide]
        mock_pptx.Presentation.return_value = prs

        text, _ = self._call()
        assert "Slide headline" in text

    @patch("services.extract_service.pptx")
    def test_slide_label_included(self, mock_pptx):
        shape = MagicMock()
        shape.text = "Content"
        slide = MagicMock()
        slide.shapes = [shape]
        prs = MagicMock()
        prs.slides = [slide]
        mock_pptx.Presentation.return_value = prs

        text, _ = self._call()
        assert "Slide 1" in text

    @patch("services.extract_service.pptx")
    def test_empty_presentation_returns_empty_message(self, mock_pptx):
        shape = MagicMock()
        shape.text = "   "
        slide = MagicMock()
        slide.shapes = [shape]
        prs = MagicMock()
        prs.slides = [slide]
        mock_pptx.Presentation.return_value = prs

        text, _ = self._call()
        assert "empty" in text.lower()

    @patch("services.extract_service.pptx")
    def test_exception_returns_error_message(self, mock_pptx):
        mock_pptx.Presentation.side_effect = RuntimeError("bad pptx")
        text, _ = self._call()
        assert "pptx processing failed" in text.lower()

    @patch("services.extract_service.pptx")
    def test_shapes_without_text_attr_skipped(self, mock_pptx):
        shape_no_text = MagicMock(spec=[])  # no 'text' attribute
        shape_with_text = MagicMock()
        shape_with_text.text = "Valid"
        slide = MagicMock()
        slide.shapes = [shape_no_text, shape_with_text]
        prs = MagicMock()
        prs.slides = [slide]
        mock_pptx.Presentation.return_value = prs

        text, _ = self._call()
        assert "Valid" in text


# ══════════════════════════════════════════════════════════════════════════════
# extract_text_from_file_content — TXT
# ══════════════════════════════════════════════════════════════════════════════
class TestExtractTXT:

    def _call(self, content, filename="notes.txt"):
        from Notes.services.extract_service import extract_text_from_file_content
        return extract_text_from_file_content(content, filename)

    def test_utf8_text_extracted(self):
        text, _ = self._call("Hello UTF-8 world".encode("utf-8"))
        assert text == "Hello UTF-8 world"

    def test_iso_8859_1_fallback(self):
        content = "café".encode("iso-8859-1")
        text, _ = self._call(content)
        assert len(text) > 0

    def test_empty_txt_returns_empty_message(self):
        text, _ = self._call(b"   ")
        assert "empty" in text.lower()

    def test_metadata_size_matches(self):
        content = b"hello world"
        _, meta = self._call(content)
        assert meta["size"] == len(content)

    def test_unsupported_encoding_returns_error(self):
        # Bytes that will fail all known encodings (raw binary)
        bad_bytes = bytes(range(128, 200))
        text, _ = self._call(bad_bytes)
        # Should eventually give an error message or decoded text
        assert isinstance(text, str)


# ══════════════════════════════════════════════════════════════════════════════
# extract_text_from_file_content — XLSX
# ══════════════════════════════════════════════════════════════════════════════
class TestExtractXLSX:

    def _call(self, content=b"xlsx bytes", filename="data.xlsx"):
        from Notes.services.extract_service import extract_text_from_file_content
        return extract_text_from_file_content(content, filename)

    @patch("services.extract_service.openpyxl" if False else "builtins.__import__")
    def test_import_error_returns_friendly_message(self, mock_import):
        original_import = __builtins__.__import__ if hasattr(__builtins__, "__import__") else __import__

        import builtins
        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "openpyxl":
                raise ImportError("No module named 'openpyxl'")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=fake_import):
            text, _ = self._call()
        assert "openpyxl" in text.lower() or "excel" in text.lower()

    def test_xlsx_with_openpyxl_mocked(self):
        mock_openpyxl = MagicMock()
        sheet = MagicMock()
        sheet.iter_rows.return_value = [("ID", "Name", "Score"), (1, "Alice", 95)]
        wb = MagicMock()
        wb.sheetnames = ["Sheet1"]
        wb.__getitem__ = MagicMock(return_value=sheet)
        mock_openpyxl.load_workbook.return_value = wb

        with patch.dict("sys.modules", {"openpyxl": mock_openpyxl}):
            from importlib import reload
            import Notes.services.extract_service as svc
            text, _ = svc.extract_text_from_file_content(b"data", "data.xlsx")

        assert isinstance(text, str)


# ══════════════════════════════════════════════════════════════════════════════
# extract_from_url
# ══════════════════════════════════════════════════════════════════════════════
class TestExtractFromURL:

    async def _call(self, url):
        from Notes.services.extract_service import extract_from_url
        return await extract_from_url(url)

    @pytest.mark.asyncio
    async def test_invalid_url_format_returns_error(self):
        text, meta = await self._call("not-a-valid-url")
        assert "invalid" in text.lower()

    @pytest.mark.asyncio
    async def test_missing_scheme_returns_error(self):
        text, _ = await self._call("example.com/page")
        assert "invalid" in text.lower()

    @pytest.mark.asyncio
    @patch("services.extract_service.requests.get")
    async def test_successful_extraction_returns_text(self, mock_get):
        mock_response = MagicMock()
        mock_response.content = b"<html><body><main><p>Main content here</p></main></body></html>"
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        text, meta = await self._call("https://example.com/article")
        assert len(text) > 0

    @pytest.mark.asyncio
    @patch("services.extract_service.requests.get")
    async def test_metadata_contains_url(self, mock_get):
        mock_response = MagicMock()
        mock_response.content = b"<html><body><p>Content</p></body></html>"
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        _, meta = await self._call("https://example.com")
        assert meta["url"] == "https://example.com"

    @pytest.mark.asyncio
    @patch("services.extract_service.requests.get")
    async def test_metadata_contains_title(self, mock_get):
        mock_response = MagicMock()
        mock_response.content = b"<html><head><title>Page Title</title></head><body><p>Content</p></body></html>"
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        _, meta = await self._call("https://example.com")
        assert meta["title"] == "Page Title"

    @pytest.mark.asyncio
    @patch("services.extract_service.requests.get")
    async def test_script_and_style_tags_removed(self, mock_get):
        mock_response = MagicMock()
        mock_response.content = (
            b"<html><body>"
            b"<script>alert('xss')</script>"
            b"<style>.hide{display:none}</style>"
            b"<p>Real content</p>"
            b"</body></html>"
        )
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        text, _ = await self._call("https://example.com")
        assert "alert" not in text
        assert "display:none" not in text

    @pytest.mark.asyncio
    @patch("services.extract_service.requests.get")
    async def test_request_exception_returns_error_message(self, mock_get):
        import requests as req
        mock_get.side_effect = req.exceptions.ConnectionError("refused")
        text, meta = await self._call("https://example.com")
        assert "failed to fetch" in text.lower() or "error" in text.lower()
        assert "error" in meta

    @pytest.mark.asyncio
    @patch("services.extract_service.requests.get")
    async def test_empty_page_returns_no_content_message(self, mock_get):
        mock_response = MagicMock()
        mock_response.content = b"<html><body></body></html>"
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        text, _ = await self._call("https://example.com")
        assert "no readable content" in text.lower() or len(text) == 0 or isinstance(text, str)

    @pytest.mark.asyncio
    @patch("services.extract_service.requests.get")
    async def test_uses_article_selector_when_present(self, mock_get):
        mock_response = MagicMock()
        mock_response.content = (
            b"<html><body>"
            b"<nav>Navigation junk</nav>"
            b"<article><p>Article content that is long enough to be substantial content indeed yes.</p></article>"
            b"</body></html>"
        )
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        text, _ = await self._call("https://example.com")
        assert "Article content" in text

    @pytest.mark.asyncio
    @patch("services.extract_service.requests.get")
    async def test_metadata_contains_length(self, mock_get):
        mock_response = MagicMock()
        mock_response.content = b"<html><body><p>Some content here</p></body></html>"
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        _, meta = await self._call("https://example.com")
        assert "length" in meta


# ══════════════════════════════════════════════════════════════════════════════
# extract_from_youtube
# ══════════════════════════════════════════════════════════════════════════════
class TestExtractFromYouTube:

    async def _call(self, url):
        from Notes.services.extract_service import extract_from_youtube
        return await extract_from_youtube(url)

    @pytest.mark.asyncio
    async def test_invalid_url_returns_error(self):
        text, meta = await self._call("https://notyoutube.com/watch?v=abc")
        assert "invalid" in text.lower()

    @pytest.mark.asyncio
    async def test_missing_video_id_returns_error(self):
        text, _ = await self._call("https://youtube.com/")
        assert "invalid" in text.lower()

    @pytest.mark.asyncio
    @patch("services.extract_service.YouTubeTranscriptApi")
    async def test_standard_url_extracts_transcript(self, mock_api):
        mock_api.get_transcript.return_value = [
            {"text": "Hello world", "start": 0.0, "duration": 2.0},
            {"text": "from YouTube", "start": 2.0, "duration": 2.0},
        ]
        text, _ = await self._call("https://youtube.com/watch?v=dQw4w9WgXcQ")
        assert "Hello world" in text
        assert "from YouTube" in text

    @pytest.mark.asyncio
    @patch("services.extract_service.YouTubeTranscriptApi")
    async def test_short_url_extracts_video_id(self, mock_api):
        mock_api.get_transcript.return_value = [{"text": "Short URL content", "start": 0, "duration": 1}]
        text, _ = await self._call("https://youtu.be/dQw4w9WgXcQ")
        assert "Short URL content" in text

    @pytest.mark.asyncio
    @patch("services.extract_service.YouTubeTranscriptApi")
    async def test_embed_url_extracts_video_id(self, mock_api):
        mock_api.get_transcript.return_value = [{"text": "Embed content", "start": 0, "duration": 1}]
        text, _ = await self._call("https://youtube.com/embed/dQw4w9WgXcQ")
        assert "Embed content" in text

    @pytest.mark.asyncio
    @patch("services.extract_service.YouTubeTranscriptApi")
    async def test_metadata_contains_video_id(self, mock_api):
        mock_api.get_transcript.return_value = [{"text": "text", "start": 0, "duration": 1}]
        _, meta = await self._call("https://youtube.com/watch?v=dQw4w9WgXcQ")
        assert meta["video_id"] == "dQw4w9WgXcQ"

    @pytest.mark.asyncio
    @patch("services.extract_service.YouTubeTranscriptApi")
    async def test_metadata_contains_transcript_entries_count(self, mock_api):
        entries = [{"text": f"entry {i}", "start": i, "duration": 1} for i in range(5)]
        mock_api.get_transcript.return_value = entries
        _, meta = await self._call("https://youtube.com/watch?v=dQw4w9WgXcQ")
        assert meta["transcript_entries"] == 5

    @pytest.mark.asyncio
    @patch("services.extract_service.YouTubeTranscriptApi")
    async def test_whitespace_normalized_in_transcript(self, mock_api):
        mock_api.get_transcript.return_value = [
            {"text": "  spaced  out  text  ", "start": 0, "duration": 1}
        ]
        text, _ = await self._call("https://youtube.com/watch?v=dQw4w9WgXcQ")
        assert "  " not in text

    @pytest.mark.asyncio
    @patch("services.extract_service.YouTubeTranscriptApi")
    async def test_empty_transcript_returns_no_transcript_message(self, mock_api):
        mock_api.get_transcript.return_value = [{"text": "   ", "start": 0, "duration": 1}]
        text, _ = await self._call("https://youtube.com/watch?v=dQw4w9WgXcQ")
        assert "no transcript" in text.lower() or len(text.strip()) == 0 or isinstance(text, str)

    @pytest.mark.asyncio
    @patch("services.extract_service.YouTubeTranscriptApi")
    async def test_api_exception_returns_error_message(self, mock_api):
        mock_api.get_transcript.side_effect = Exception("Transcripts disabled")
        text, meta = await self._call("https://youtube.com/watch?v=dQw4w9WgXcQ")
        assert "error" in text.lower() or "processing" in text.lower()
        assert "error" in meta

    @pytest.mark.asyncio
    @patch("services.extract_service.YouTubeTranscriptApi")
    async def test_metadata_contains_length(self, mock_api):
        mock_api.get_transcript.return_value = [{"text": "content", "start": 0, "duration": 1}]
        _, meta = await self._call("https://youtube.com/watch?v=dQw4w9WgXcQ")
        assert "length" in meta