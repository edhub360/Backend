# tests/unit/notes/test_models.py

import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.orm import RelationshipProperty


# ══════════════════════════════════════════════════════════════════════════════
# Import models once (patch heavy deps at module level)
# ══════════════════════════════════════════════════════════════════════════════
@pytest.fixture(scope="module", autouse=True)
def patch_pgvector():
    """pgvector may not be installed in CI — stub it out."""
    vector_mock = MagicMock()
    vector_mock.Vector = lambda dim: MagicMock()
    with patch.dict("sys.modules", {"pgvector": vector_mock, "pgvector.sqlalchemy": vector_mock}):
        yield


@pytest.fixture(scope="module")
def models():
    import importlib
    import models as m
    return m


# ══════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════
def _col(model, name):
    return model.__table__.c[name]


def _rel(model, name) -> RelationshipProperty:
    return sa_inspect(model).relationships[name]


# ══════════════════════════════════════════════════════════════════════════════
# Notebook
# ══════════════════════════════════════════════════════════════════════════════
class TestNotebookModel:

    def test_tablename(self, models):
        assert models.Notebook.__tablename__ == "notebooks"

    def test_schema(self, models):
        assert models.Notebook.__table_args__["schema"] == "stud_hub_schema"

    def test_id_is_primary_key(self, models):
        assert _col(models.Notebook, "id").primary_key

    def test_id_has_server_default(self, models):
        assert _col(models.Notebook, "id").server_default is not None

    def test_user_id_not_nullable(self, models):
        assert not _col(models.Notebook, "user_id").nullable

    def test_user_id_is_indexed(self, models):
        assert _col(models.Notebook, "user_id").index

    def test_title_not_nullable(self, models):
        assert not _col(models.Notebook, "title").nullable

    def test_created_at_has_server_default(self, models):
        assert _col(models.Notebook, "created_at").server_default is not None

    def test_updated_at_is_nullable(self, models):
        assert _col(models.Notebook, "updated_at").nullable

    def test_sources_relationship_exists(self, models):
        rel = _rel(models.Notebook, "sources")
        assert rel is not None

    def test_sources_cascade_includes_delete_orphan(self, models):
        rel = _rel(models.Notebook, "sources")
        assert "delete-orphan" in rel.cascade

    def test_sources_cascade_includes_all(self, models):
        rel = _rel(models.Notebook, "sources")
        assert "all" in rel.cascade or "delete" in rel.cascade

    def test_sources_passive_deletes(self, models):
        rel = _rel(models.Notebook, "sources")
        assert rel.passive_deletes is True

    def test_sources_back_populates_notebook(self, models):
        rel = _rel(models.Notebook, "sources")
        assert rel.back_populates == "notebook"

    def test_inherits_from_base(self, models):
        from db import Base
        assert issubclass(models.Notebook, Base)


# ══════════════════════════════════════════════════════════════════════════════
# Source
# ══════════════════════════════════════════════════════════════════════════════
class TestSourceModel:

    def test_tablename(self, models):
        assert models.Source.__tablename__ == "sources"

    def test_schema(self, models):
        assert models.Source.__table_args__["schema"] == "stud_hub_schema"

    def test_id_is_primary_key(self, models):
        assert _col(models.Source, "id").primary_key

    def test_notebook_id_not_nullable(self, models):
        assert not _col(models.Source, "notebook_id").nullable

    def test_notebook_id_has_foreign_key(self, models):
        fks = list(_col(models.Source, "notebook_id").foreign_keys)
        assert len(fks) == 1

    def test_notebook_id_fk_references_notebooks(self, models):
        fk = next(iter(_col(models.Source, "notebook_id").foreign_keys))
        assert "notebooks.id" in fk.target_fullname

    def test_notebook_id_fk_on_delete_cascade(self, models):
        fk = next(iter(_col(models.Source, "notebook_id").foreign_keys))
        assert fk.ondelete == "CASCADE"

    def test_type_not_nullable(self, models):
        assert not _col(models.Source, "type").nullable

    def test_filename_is_nullable(self, models):
        assert _col(models.Source, "filename").nullable

    def test_file_url_is_nullable(self, models):
        assert _col(models.Source, "file_url").nullable

    def test_website_url_is_nullable(self, models):
        assert _col(models.Source, "website_url").nullable

    def test_youtube_url_is_nullable(self, models):
        assert _col(models.Source, "youtube_url").nullable

    def test_extracted_text_is_nullable(self, models):
        assert _col(models.Source, "extracted_text").nullable

    def test_source_metadata_is_nullable(self, models):
        assert _col(models.Source, "source_metadata").nullable

    def test_created_at_has_server_default(self, models):
        assert _col(models.Source, "created_at").server_default is not None

    def test_notebook_relationship_exists(self, models):
        assert _rel(models.Source, "notebook") is not None

    def test_notebook_back_populates_sources(self, models):
        rel = _rel(models.Source, "notebook")
        assert rel.back_populates == "sources"

    def test_embeddings_relationship_exists(self, models):
        assert _rel(models.Source, "embeddings") is not None

    def test_embeddings_back_populates_source(self, models):
        rel = _rel(models.Source, "embeddings")
        assert rel.back_populates == "source"

    def test_inherits_from_base(self, models):
        from db import Base
        assert issubclass(models.Source, Base)


# ══════════════════════════════════════════════════════════════════════════════
# Embedding
# ══════════════════════════════════════════════════════════════════════════════
class TestEmbeddingModel:

    def test_tablename(self, models):
        assert models.Embedding.__tablename__ == "embeddings"

    def test_schema(self, models):
        assert models.Embedding.__table_args__["schema"] == "stud_hub_schema"

    def test_id_is_primary_key(self, models):
        assert _col(models.Embedding, "id").primary_key

    def test_source_id_not_nullable(self, models):
        assert not _col(models.Embedding, "source_id").nullable

    def test_source_id_has_foreign_key(self, models):
        fks = list(_col(models.Embedding, "source_id").foreign_keys)
        assert len(fks) == 1

    def test_source_id_fk_references_sources(self, models):
        fk = next(iter(_col(models.Embedding, "source_id").foreign_keys))
        assert "sources.id" in fk.target_fullname

    def test_source_id_fk_on_delete_cascade(self, models):
        fk = next(iter(_col(models.Embedding, "source_id").foreign_keys))
        assert fk.ondelete == "CASCADE"

    def test_chunk_not_nullable(self, models):
        assert not _col(models.Embedding, "chunk").nullable

    def test_vector_column_exists(self, models):
        assert "vector" in models.Embedding.__table__.c

    def test_vector_not_nullable(self, models):
        assert not _col(models.Embedding, "vector").nullable

    def test_created_at_has_server_default(self, models):
        assert _col(models.Embedding, "created_at").server_default is not None

    def test_source_relationship_exists(self, models):
        assert _rel(models.Embedding, "source") is not None

    def test_source_back_populates_embeddings(self, models):
        rel = _rel(models.Embedding, "source")
        assert rel.back_populates == "embeddings"

    def test_inherits_from_base(self, models):
        from db import Base
        assert issubclass(models.Embedding, Base)


# ══════════════════════════════════════════════════════════════════════════════
# Cross-model relationship symmetry
# ══════════════════════════════════════════════════════════════════════════════
class TestRelationshipSymmetry:

    def test_notebook_sources_links_to_source_model(self, models):
        rel = _rel(models.Notebook, "sources")
        assert rel.mapper.class_ is models.Source

    def test_source_notebook_links_to_notebook_model(self, models):
        rel = _rel(models.Source, "notebook")
        assert rel.mapper.class_ is models.Notebook

    def test_source_embeddings_links_to_embedding_model(self, models):
        rel = _rel(models.Source, "embeddings")
        assert rel.mapper.class_ is models.Embedding

    def test_embedding_source_links_to_source_model(self, models):
        rel = _rel(models.Embedding, "source")
        assert rel.mapper.class_ is models.Source