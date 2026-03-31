# tests/unit/ai_chat/test_text_processing.py

import pytest
from unittest.mock import patch, MagicMock


# ─────────────────────────────────────────────
# extract_text_from_pdf
# ─────────────────────────────────────────────

class TestExtractTextFromPdf:

    @patch("ai_chat.app.utils.text_processing.PdfReader")
    def test_returns_extracted_text(self, mock_reader_cls):
        from ai_chat.app.utils.text_processing import extract_text_from_pdf

        page = MagicMock()
        page.extract_text.return_value = "Hello from PDF"
        mock_reader_cls.return_value.pages = [page]

        result = extract_text_from_pdf(b"fake pdf bytes")

        assert result == "Hello from PDF"

    @patch("ai_chat.app.utils.text_processing.PdfReader")
    def test_joins_multiple_pages_with_newline(self, mock_reader_cls):
        from ai_chat.app.utils.text_processing import extract_text_from_pdf

        pages = [MagicMock(), MagicMock()]
        pages[0].extract_text.return_value = "Page one text"
        pages[1].extract_text.return_value = "Page two text"
        mock_reader_cls.return_value.pages = pages

        result = extract_text_from_pdf(b"pdf")

        assert result == "Page one text\nPage two text"

    @patch("ai_chat.app.utils.text_processing.PdfReader")
    def test_skips_blank_pages(self, mock_reader_cls):
        from ai_chat.app.utils.text_processing import extract_text_from_pdf

        pages = [MagicMock(), MagicMock(), MagicMock()]
        pages[0].extract_text.return_value = "Real content"
        pages[1].extract_text.return_value = "   "       # whitespace only
        pages[2].extract_text.return_value = "More content"
        mock_reader_cls.return_value.pages = pages

        result = extract_text_from_pdf(b"pdf")

        assert result == "Real content\nMore content"

    @patch("ai_chat.app.utils.text_processing.PdfReader")
    def test_all_blank_pages_returns_empty_string(self, mock_reader_cls):
        from ai_chat.app.utils.text_processing import extract_text_from_pdf

        page = MagicMock()
        page.extract_text.return_value = "   "
        mock_reader_cls.return_value.pages = [page]

        result = extract_text_from_pdf(b"pdf")

        assert result == ""

    @patch("ai_chat.app.utils.text_processing.PdfReader")
    def test_empty_pages_list_returns_empty_string(self, mock_reader_cls):
        from ai_chat.app.utils.text_processing import extract_text_from_pdf

        mock_reader_cls.return_value.pages = []

        result = extract_text_from_pdf(b"pdf")

        assert result == ""

    @patch("ai_chat.app.utils.text_processing.PdfReader")
    def test_reader_exception_raises_value_error(self, mock_reader_cls):
        from ai_chat.app.utils.text_processing import extract_text_from_pdf

        mock_reader_cls.side_effect = Exception("corrupt pdf")

        with pytest.raises(ValueError, match="Error processing PDF"):
            extract_text_from_pdf(b"bad")

    @patch("ai_chat.app.utils.text_processing.PdfReader")
    def test_value_error_wraps_original_message(self, mock_reader_cls):
        from ai_chat.app.utils.text_processing import extract_text_from_pdf

        mock_reader_cls.side_effect = Exception("bad xref table")

        with pytest.raises(ValueError) as exc_info:
            extract_text_from_pdf(b"bad")

        assert "bad xref table" in str(exc_info.value)

    @patch("ai_chat.app.utils.text_processing.PdfReader")
    def test_passes_bytes_wrapped_in_bytesio(self, mock_reader_cls):
        from ai_chat.app.utils.text_processing import extract_text_from_pdf
        import io

        page = MagicMock()
        page.extract_text.return_value = "text"
        mock_reader_cls.return_value.pages = [page]

        extract_text_from_pdf(b"pdfbytes")

        args, _ = mock_reader_cls.call_args
        assert isinstance(args[0], io.BytesIO)


# ─────────────────────────────────────────────
# extract_text_from_docx
# ─────────────────────────────────────────────

class TestExtractTextFromDocx:

    @patch("ai_chat.app.utils.text_processing.Document")
    def test_returns_paragraph_text(self, mock_doc_cls):
        from ai_chat.app.utils.text_processing import extract_text_from_docx

        para = MagicMock()
        para.text = "This is a paragraph."
        mock_doc_cls.return_value.paragraphs = [para]

        result = extract_text_from_docx(b"docx bytes")

        assert result == "This is a paragraph."

    @patch("ai_chat.app.utils.text_processing.Document")
    def test_joins_multiple_paragraphs_with_newline(self, mock_doc_cls):
        from ai_chat.app.utils.text_processing import extract_text_from_docx

        paras = [MagicMock(), MagicMock()]
        paras[0].text = "First paragraph"
        paras[1].text = "Second paragraph"
        mock_doc_cls.return_value.paragraphs = paras

        result = extract_text_from_docx(b"docx")

        assert result == "First paragraph\nSecond paragraph"

    @patch("ai_chat.app.utils.text_processing.Document")
    def test_skips_empty_paragraphs(self, mock_doc_cls):
        from ai_chat.app.utils.text_processing import extract_text_from_docx

        paras = [MagicMock(), MagicMock(), MagicMock()]
        paras[0].text = "Real text"
        paras[1].text = "   "   # whitespace — should be skipped
        paras[2].text = "More text"
        mock_doc_cls.return_value.paragraphs = paras

        result = extract_text_from_docx(b"docx")

        assert result == "Real text\nMore text"

    @patch("ai_chat.app.utils.text_processing.Document")
    def test_all_empty_paragraphs_returns_empty_string(self, mock_doc_cls):
        from ai_chat.app.utils.text_processing import extract_text_from_docx

        para = MagicMock()
        para.text = ""
        mock_doc_cls.return_value.paragraphs = [para]

        result = extract_text_from_docx(b"docx")

        assert result == ""

    @patch("ai_chat.app.utils.text_processing.Document")
    def test_no_paragraphs_returns_empty_string(self, mock_doc_cls):
        from ai_chat.app.utils.text_processing import extract_text_from_docx

        mock_doc_cls.return_value.paragraphs = []

        result = extract_text_from_docx(b"docx")

        assert result == ""

    @patch("ai_chat.app.utils.text_processing.Document")
    def test_exception_raises_value_error(self, mock_doc_cls):
        from ai_chat.app.utils.text_processing import extract_text_from_docx

        mock_doc_cls.side_effect = Exception("bad docx")

        with pytest.raises(ValueError, match="Error processing DOCX"):
            extract_text_from_docx(b"bad")

    @patch("ai_chat.app.utils.text_processing.Document")
    def test_value_error_wraps_original_message(self, mock_doc_cls):
        from ai_chat.app.utils.text_processing import extract_text_from_docx

        mock_doc_cls.side_effect = Exception("zip file error")

        with pytest.raises(ValueError) as exc_info:
            extract_text_from_docx(b"bad")

        assert "zip file error" in str(exc_info.value)

    @patch("ai_chat.app.utils.text_processing.Document")
    def test_passes_bytes_wrapped_in_bytesio(self, mock_doc_cls):
        from ai_chat.app.utils.text_processing import extract_text_from_docx
        import io

        mock_doc_cls.return_value.paragraphs = []

        extract_text_from_docx(b"docxbytes")

        args, _ = mock_doc_cls.call_args
        assert isinstance(args[0], io.BytesIO)


# ─────────────────────────────────────────────
# extract_text_from_txt
# ─────────────────────────────────────────────

class TestExtractTextFromTxt:

    def test_decodes_utf8_bytes(self):
        from ai_chat.app.utils.text_processing import extract_text_from_txt

        result = extract_text_from_txt("hello world".encode("utf-8"))

        assert result == "hello world"

    def test_preserves_newlines(self):
        from ai_chat.app.utils.text_processing import extract_text_from_txt

        result = extract_text_from_txt(b"line one\nline two\nline three")

        assert result == "line one\nline two\nline three"

    def test_ignores_non_utf8_bytes(self):
        from ai_chat.app.utils.text_processing import extract_text_from_txt

        result = extract_text_from_txt(b"valid\xff\xfeinvalid bytes")

        assert "valid" in result

    def test_empty_bytes_returns_empty_string(self):
        from ai_chat.app.utils.text_processing import extract_text_from_txt

        result = extract_text_from_txt(b"")

        assert result == ""

    def test_unicode_content_preserved(self):
        from ai_chat.app.utils.text_processing import extract_text_from_txt

        text = "தமிழ் உரை"  # Tamil script
        result = extract_text_from_txt(text.encode("utf-8"))

        assert result == text


# ─────────────────────────────────────────────
# extract_text (dispatcher)
# ─────────────────────────────────────────────

class TestExtractText:

    @patch("ai_chat.app.utils.text_processing.extract_text_from_pdf")
    def test_routes_pdf_to_pdf_extractor(self, mock_pdf):
        from ai_chat.app.utils.text_processing import extract_text

        mock_pdf.return_value = "pdf content"
        result = extract_text("document.pdf", b"bytes")

        mock_pdf.assert_called_once_with(b"bytes")
        assert result == "pdf content"

    @patch("ai_chat.app.utils.text_processing.extract_text_from_docx")
    def test_routes_docx_to_docx_extractor(self, mock_docx):
        from ai_chat.app.utils.text_processing import extract_text

        mock_docx.return_value = "docx content"
        result = extract_text("report.docx", b"bytes")

        mock_docx.assert_called_once_with(b"bytes")
        assert result == "docx content"

    @patch("ai_chat.app.utils.text_processing.extract_text_from_txt")
    def test_routes_txt_to_txt_extractor(self, mock_txt):
        from ai_chat.app.utils.text_processing import extract_text

        mock_txt.return_value = "plain text"
        result = extract_text("notes.txt", b"bytes")

        mock_txt.assert_called_once_with(b"bytes")
        assert result == "plain text"

    def test_unsupported_extension_raises_value_error(self):
        from ai_chat.app.utils.text_processing import extract_text

        with pytest.raises(ValueError, match="Unsupported file type"):
            extract_text("image.png", b"bytes")

    def test_unsupported_extension_error_includes_suffix(self):
        from ai_chat.app.utils.text_processing import extract_text

        with pytest.raises(ValueError) as exc_info:
            extract_text("data.csv", b"bytes")

        assert ".csv" in str(exc_info.value)

    @patch("ai_chat.app.utils.text_processing.extract_text_from_pdf")
    def test_extension_is_case_insensitive(self, mock_pdf):
        from ai_chat.app.utils.text_processing import extract_text

        mock_pdf.return_value = "ok"
        extract_text("DOCUMENT.PDF", b"bytes")

        mock_pdf.assert_called_once()

    def test_no_extension_raises_value_error(self):
        from ai_chat.app.utils.text_processing import extract_text

        with pytest.raises(ValueError, match="Unsupported file type"):
            extract_text("noextension", b"bytes")

    @patch("ai_chat.app.utils.text_processing.extract_text_from_txt")
    def test_filename_with_path_prefix_handled(self, mock_txt):
        from ai_chat.app.utils.text_processing import extract_text

        mock_txt.return_value = "content"
        result = extract_text("uploads/subdir/notes.txt", b"bytes")

        mock_txt.assert_called_once()
        assert result == "content"


# ─────────────────────────────────────────────
# chunk_text
# ─────────────────────────────────────────────

class TestChunkText:

    def test_empty_string_returns_empty_list(self):
        from ai_chat.app.utils.text_processing import chunk_text

        assert chunk_text("") == []

    def test_whitespace_only_returns_empty_list(self):
        from ai_chat.app.utils.text_processing import chunk_text

        assert chunk_text("   \n\t  ") == []

    def test_short_text_returns_single_chunk(self):
        from ai_chat.app.utils.text_processing import chunk_text

        text = "short text with few words"
        result = chunk_text(text, chunk_size=1000)

        assert result == [text]

    def test_exact_chunk_size_returns_single_chunk(self):
        from ai_chat.app.utils.text_processing import chunk_text

        words = ["word"] * 1000
        text = " ".join(words)
        result = chunk_text(text, chunk_size=1000)

        assert len(result) == 1

    def test_returns_list_type(self):
        from ai_chat.app.utils.text_processing import chunk_text

        result = chunk_text("some text here", chunk_size=1000)

        assert isinstance(result, list)

    def test_long_text_produces_multiple_chunks(self):
        from ai_chat.app.utils.text_processing import chunk_text

        words = ["word"] * 2500
        text = " ".join(words)
        result = chunk_text(text, chunk_size=1000, overlap=200)

        assert len(result) > 1

    def test_each_chunk_is_a_string(self):
        from ai_chat.app.utils.text_processing import chunk_text

        words = ["word"] * 2000
        text = " ".join(words)
        result = chunk_text(text, chunk_size=500, overlap=100)

        assert all(isinstance(c, str) for c in result)

    def test_all_words_covered_across_chunks(self):
        from ai_chat.app.utils.text_processing import chunk_text

        words = [f"w{i}" for i in range(2500)]
        text = " ".join(words)
        result = chunk_text(text, chunk_size=1000, overlap=200)

        # The first word of each chunk and last chunk must contain start/end words
        all_text = " ".join(result)
        assert "w0" in all_text
        assert "w2499" in all_text

    def test_first_chunk_starts_at_beginning(self):
        from ai_chat.app.utils.text_processing import chunk_text

        words = [f"token{i}" for i in range(2000)]
        text = " ".join(words)
        result = chunk_text(text, chunk_size=1000, overlap=200)

        assert result[0].startswith("token0")

    def test_last_chunk_ends_at_last_word(self):
        from ai_chat.app.utils.text_processing import chunk_text

        words = [f"tok{i}" for i in range(2000)]
        text = " ".join(words)
        result = chunk_text(text, chunk_size=1000, overlap=200)

        assert result[-1].endswith("tok1999")

    def test_overlap_causes_words_to_repeat_across_chunks(self):
        from ai_chat.app.utils.text_processing import chunk_text

        words = [f"w{i}" for i in range(1500)]
        text = " ".join(words)
        result = chunk_text(text, chunk_size=1000, overlap=200)

        # Words [800:1000] should appear in both chunk[0] and chunk[1]
        assert len(result) >= 2
        chunk0_words = set(result[0].split())
        chunk1_words = set(result[1].split())
        overlap_words = chunk0_words & chunk1_words
        assert len(overlap_words) > 0

    def test_zero_overlap_produces_no_repeated_words(self):
        from ai_chat.app.utils.text_processing import chunk_text

        words = [f"u{i}" for i in range(2000)]
        text = " ".join(words)
        result = chunk_text(text, chunk_size=1000, overlap=0)

        assert len(result) == 2
        assert result[0].split()[-1] == "u999"
        assert result[1].split()[0] == "u1000"

    def test_chunk_size_respected(self):
        from ai_chat.app.utils.text_processing import chunk_text

        words = ["word"] * 3000
        text = " ".join(words)
        result = chunk_text(text, chunk_size=500, overlap=0)

        for chunk in result:
            assert len(chunk.split()) <= 500

    def test_custom_chunk_size_single_word_text(self):
        from ai_chat.app.utils.text_processing import chunk_text

        result = chunk_text("only", chunk_size=10)

        assert result == ["only"]