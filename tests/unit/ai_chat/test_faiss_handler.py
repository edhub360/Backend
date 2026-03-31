# tests/unit/ai_chat/test_faiss_handler.py

import pytest
import numpy as np
import pickle
import faiss
from pathlib import Path
from unittest.mock import patch, MagicMock


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

DIM = 4  # small dimension for fast tests


def make_embeddings(n: int = 2, dim: int = DIM) -> np.ndarray:
    return np.random.rand(n, dim).astype(np.float32)


def make_store(tmp_path, dimension: int = DIM):
    """Create a fresh FaissStore pointed at tmp_path (no disk artifacts)."""
    from ai_chat.app.utils.faiss_handler import FaissStore

    with patch.dict("os.environ", {"FAISS_STORAGE_DIR": str(tmp_path)}):
        return FaissStore(dimension=dimension)


# ─────────────────────────────────────────────
# FaissStore.__init__ / _initialize_index
# ─────────────────────────────────────────────

class TestFaissStoreInit:

    def test_index_is_created_on_init(self, tmp_path):
        store = make_store(tmp_path)
        assert store.index is not None

    def test_metadata_starts_empty_when_no_existing_data(self, tmp_path):
        store = make_store(tmp_path)
        assert store.metadata == []

    def test_dimension_stored_correctly(self, tmp_path):
        store = make_store(tmp_path)
        assert store.dimension == DIM

    def test_storage_dir_created(self, tmp_path):
        target = tmp_path / "nested" / "dir"
        from ai_chat.app.utils.faiss_handler import FaissStore

        with patch.dict("os.environ", {"FAISS_STORAGE_DIR": str(target)}):
            FaissStore(dimension=DIM)

        assert target.exists()

    def test_index_ntotal_zero_on_fresh_store(self, tmp_path):
        store = make_store(tmp_path)
        assert store.index.ntotal == 0


# ─────────────────────────────────────────────
# _load_existing_data
# ─────────────────────────────────────────────

class TestLoadExistingData:

    def test_loads_saved_index_and_metadata(self, tmp_path):
        store = make_store(tmp_path)

        # populate and save
        embeddings = make_embeddings(3)
        store.add_documents(embeddings, ["a", "b", "c"], "file.pdf")

        # new instance should reload from disk
        store2 = make_store(tmp_path)
        assert store2.index.ntotal == 3
        assert len(store2.metadata) == 3

    def test_loaded_metadata_has_correct_fields(self, tmp_path):
        store = make_store(tmp_path)
        embeddings = make_embeddings(1)
        store.add_documents(embeddings, ["hello"], "notes.txt")

        store2 = make_store(tmp_path)
        assert store2.metadata[0]["text"] == "hello"
        assert store2.metadata[0]["source"] == "notes.txt"

    def test_corrupt_index_file_falls_back_to_fresh(self, tmp_path):
        store = make_store(tmp_path)

        # write garbage to the index file
        (tmp_path / "faiss_index.bin").write_bytes(b"corrupted data")
        # write valid metadata so only the index is corrupt
        with open(tmp_path / "metadata.pkl", "wb") as f:
            pickle.dump([], f)

        store2 = make_store(tmp_path)
        assert store2.index.ntotal == 0
        assert store2.metadata == []

    def test_missing_files_skips_load_silently(self, tmp_path):
        store = make_store(tmp_path)
        assert store.index is not None
        assert store.metadata == []


# ─────────────────────────────────────────────
# add_documents
# ─────────────────────────────────────────────

class TestAddDocuments:

    def test_adds_vectors_to_index(self, tmp_path):
        store = make_store(tmp_path)
        store.add_documents(make_embeddings(3), ["a", "b", "c"], "src.pdf")
        assert store.index.ntotal == 3

    def test_adds_metadata_entries(self, tmp_path):
        store = make_store(tmp_path)
        store.add_documents(make_embeddings(2), ["x", "y"], "doc.txt")
        assert len(store.metadata) == 2

    def test_metadata_text_values_correct(self, tmp_path):
        store = make_store(tmp_path)
        store.add_documents(make_embeddings(2), ["first", "second"], "src.pdf")
        assert store.metadata[0]["text"] == "first"
        assert store.metadata[1]["text"] == "second"

    def test_metadata_source_values_correct(self, tmp_path):
        store = make_store(tmp_path)
        store.add_documents(make_embeddings(2), ["a", "b"], "my_file.pdf")
        assert store.metadata[0]["source"] == "my_file.pdf"
        assert store.metadata[1]["source"] == "my_file.pdf"

    def test_mismatched_embeddings_and_texts_raises_value_error(self, tmp_path):
        store = make_store(tmp_path)
        with pytest.raises(ValueError, match="Number of embeddings must match"):
            store.add_documents(make_embeddings(3), ["only two texts", "here"], "src")

    def test_multiple_add_calls_accumulate(self, tmp_path):
        store = make_store(tmp_path)
        store.add_documents(make_embeddings(2), ["a", "b"], "file1.pdf")
        store.add_documents(make_embeddings(3), ["c", "d", "e"], "file2.pdf")
        assert store.index.ntotal == 5
        assert len(store.metadata) == 5

    def test_saves_index_file_to_disk(self, tmp_path):
        store = make_store(tmp_path)
        store.add_documents(make_embeddings(1), ["text"], "file.pdf")
        assert (tmp_path / "faiss_index.bin").exists()

    def test_saves_metadata_file_to_disk(self, tmp_path):
        store = make_store(tmp_path)
        store.add_documents(make_embeddings(1), ["text"], "file.pdf")
        assert (tmp_path / "metadata.pkl").exists()

    def test_save_failure_raises_runtime_error(self, tmp_path):
        store = make_store(tmp_path)

        with patch("ai_chat.app.utils.faiss_handler.faiss.write_index",
                   side_effect=OSError("disk full")):
            with pytest.raises(RuntimeError, match="Error saving FAISS data"):
                store.add_documents(make_embeddings(1), ["text"], "file.pdf")


# ─────────────────────────────────────────────
# search
# ─────────────────────────────────────────────

class TestSearch:

    def test_empty_index_returns_empty_list(self, tmp_path):
        store = make_store(tmp_path)
        query = make_embeddings(1)
        result = store.search(query, k=5)
        assert result == []

    def test_returns_list_of_tuples(self, tmp_path):
        store = make_store(tmp_path)
        store.add_documents(make_embeddings(3), ["a", "b", "c"], "f.pdf")
        results = store.search(make_embeddings(1), k=2)

        assert isinstance(results, list)
        assert all(isinstance(r, tuple) and len(r) == 3 for r in results)

    def test_result_tuple_fields(self, tmp_path):
        store = make_store(tmp_path)
        store.add_documents(make_embeddings(1), ["hello doc"], "notes.txt")
        results = store.search(make_embeddings(1), k=1)

        text, source, distance = results[0]
        assert isinstance(text, str)
        assert isinstance(source, str)
        assert isinstance(distance, float)

    def test_respects_k_limit(self, tmp_path):
        store = make_store(tmp_path)
        store.add_documents(make_embeddings(5), ["a", "b", "c", "d", "e"], "f.pdf")
        results = store.search(make_embeddings(1), k=3)
        assert len(results) <= 3

    def test_k_larger_than_index_returns_all(self, tmp_path):
        store = make_store(tmp_path)
        store.add_documents(make_embeddings(2), ["x", "y"], "f.pdf")
        results = store.search(make_embeddings(1), k=100)
        assert len(results) == 2

    def test_1d_query_is_reshaped_automatically(self, tmp_path):
        store = make_store(tmp_path)
        store.add_documents(make_embeddings(2), ["a", "b"], "f.pdf")

        query_1d = np.random.rand(DIM).astype(np.float32)  # 1D
        results = store.search(query_1d, k=1)
        assert len(results) == 1

    def test_exact_match_returns_zero_distance(self, tmp_path):
        store = make_store(tmp_path)
        vec = np.ones((1, DIM), dtype=np.float32)
        store.add_documents(vec, ["exact"], "src")

        results = store.search(vec, k=1)
        assert results[0][2] == pytest.approx(0.0, abs=1e-5)

    def test_closest_vector_ranked_first(self, tmp_path):
        store = make_store(tmp_path)

        # Add a zero vector and a far vector
        zero_vec = np.zeros((1, DIM), dtype=np.float32)
        far_vec = np.ones((1, DIM), dtype=np.float32) * 100

        store.add_documents(zero_vec, ["near"], "src")
        store.add_documents(far_vec, ["far"], "src")

        query = np.zeros((1, DIM), dtype=np.float32)
        results = store.search(query, k=2)

        assert results[0][0] == "near"
        assert results[0][2] < results[1][2]

    def test_source_preserved_in_results(self, tmp_path):
        store = make_store(tmp_path)
        store.add_documents(make_embeddings(1), ["text"], "lecture_notes.pdf")
        results = store.search(make_embeddings(1), k=1)
        assert results[0][1] == "lecture_notes.pdf"


# ─────────────────────────────────────────────
# get_stats
# ─────────────────────────────────────────────

class TestGetStats:

    def test_empty_store_stats(self, tmp_path):
        store = make_store(tmp_path)
        stats = store.get_stats()
        assert stats["total_vectors"] == 0
        assert stats["total_documents"] == 0
        assert stats["dimension"] == DIM

    def test_stats_after_adding_documents(self, tmp_path):
        store = make_store(tmp_path)
        store.add_documents(make_embeddings(3), ["a", "b", "c"], "file.pdf")
        stats = store.get_stats()
        assert stats["total_vectors"] == 3

    def test_total_documents_counts_unique_sources(self, tmp_path):
        store = make_store(tmp_path)
        store.add_documents(make_embeddings(2), ["a", "b"], "file1.pdf")
        store.add_documents(make_embeddings(2), ["c", "d"], "file2.pdf")
        store.add_documents(make_embeddings(1), ["e"], "file1.pdf")  # duplicate source

        stats = store.get_stats()
        assert stats["total_documents"] == 2  # only 2 unique sources

    def test_stats_dimension_matches_init(self, tmp_path):
        store = make_store(tmp_path, dimension=DIM)
        assert store.get_stats()["dimension"] == DIM

    def test_stats_returns_dict(self, tmp_path):
        store = make_store(tmp_path)
        assert isinstance(store.get_stats(), dict)


# ─────────────────────────────────────────────
# get_faiss_store (singleton)
# ─────────────────────────────────────────────

class TestGetFaissStore:

    def test_returns_faiss_store_instance(self, tmp_path):
        from ai_chat.app.utils.faiss_handler import FaissStore

        with patch.dict("os.environ", {"FAISS_STORAGE_DIR": str(tmp_path)}):
            with patch("ai_chat.app.utils.faiss_handler._faiss_store", None):
                from ai_chat.app.utils.faiss_handler import get_faiss_store
                store = get_faiss_store(dimension=DIM)

        assert isinstance(store, FaissStore)

    def test_returns_same_instance_on_repeated_calls(self, tmp_path):
        with patch.dict("os.environ", {"FAISS_STORAGE_DIR": str(tmp_path)}):
            with patch("ai_chat.app.utils.faiss_handler._faiss_store", None):
                from ai_chat.app.utils.faiss_handler import get_faiss_store
                store1 = get_faiss_store(dimension=DIM)
                store2 = get_faiss_store(dimension=DIM)

        assert store1 is store2

    def test_existing_instance_is_reused_ignoring_dimension_arg(self, tmp_path):
        """Once created, dimension arg on subsequent calls is ignored."""
        with patch.dict("os.environ", {"FAISS_STORAGE_DIR": str(tmp_path)}):
            with patch("ai_chat.app.utils.faiss_handler._faiss_store", None):
                from ai_chat.app.utils.faiss_handler import get_faiss_store
                store1 = get_faiss_store(dimension=DIM)
                store2 = get_faiss_store(dimension=512)  # different dim, but ignored

        assert store1 is store2