"""tests/unit/cs_bot/conftest.py"""
import sys
from unittest.mock import MagicMock, AsyncMock

# Block the entire broken langchain import chain at process start
_mocks = {
    "langchain_core":                                MagicMock(),
    "langchain_core._api":                           MagicMock(),
    "langchain_core._api.deprecation":               MagicMock(),
    "langchain_core.chat_history":                   MagicMock(),
    "langchain_core.documents":                      MagicMock(),
    "langchain_core.documents.base":                 MagicMock(),
    "langchain_core.messages":                       MagicMock(),
    "langchain_core.messages.base":                  MagicMock(),
    "langchain_core.messages.human":                 MagicMock(),
    "langchain_core.messages.ai":                    MagicMock(),
    "langchain_core.embeddings":                     MagicMock(),
    "langchain_core.vectorstores":                   MagicMock(),
    "langchain_core.runnables":                      MagicMock(),
    "langchain_core.runnables.base":                 MagicMock(),
    "langchain_core.runnables.config":               MagicMock(),
    "langchain_core.output_parsers":                 MagicMock(),
    "langchain_core.prompts":                        MagicMock(),
    "langchain_core.prompts.chat":                   MagicMock(),
    "langchain_core.language_models":                MagicMock(),
    "langchain_core.language_models.chat_models":    MagicMock(),
    "langchain_core.retrievers":                     MagicMock(),
    "langchain_core.callbacks":                      MagicMock(),
    "langchain_core.callbacks.manager":              MagicMock(),
    "langchain_core.pydantic_v1":                    MagicMock(),
    "langchain_core.tools":                          MagicMock(),
    "langchain_core.utils":                          MagicMock(),
    "langchain_postgres":                            MagicMock(),
    "langchain_postgres.vectorstores":               MagicMock(),
    "langchain_postgres.chat_message_histories":     MagicMock(),
    "langchain_community":                           MagicMock(),
    "langchain_community.document_loaders":          MagicMock(),
    "langchain_community.document_loaders.web_base": MagicMock(),
    "langchain_google_genai":                        MagicMock(),
    "langchain_google_genai.embeddings":             MagicMock(),
    "langchain_text_splitters":                      MagicMock(),
}
sys.modules.update(_mocks)

# Real message classes — session_service uses isinstance + .type + .content
class HumanMessage:
    type = "human"
    def __init__(self, content=""):
        self.content = content

class AIMessage:
    type = "ai"
    def __init__(self, content=""):
        self.content = content

class BaseMessage:
    pass

sys.modules["langchain_core.messages"].HumanMessage = HumanMessage
sys.modules["langchain_core.messages"].AIMessage    = AIMessage
sys.modules["langchain_core.messages"].BaseMessage  = BaseMessage
sys.modules["langchain_core"].HumanMessage = HumanMessage
sys.modules["langchain_core"].AIMessage    = AIMessage

# Real Document class — ingestion/rag use .page_content and .metadata
class Document:
    def __init__(self, page_content="", metadata=None):
        self.page_content = page_content
        self.metadata     = metadata if metadata is not None else {}

sys.modules["langchain_core.documents"].Document      = Document
sys.modules["langchain_core.documents.base"].Document = Document

# Attribute shortcuts used by patch targets
sys.modules["langchain_postgres"].PGVector = MagicMock
sys.modules["langchain_google_genai"].GoogleGenerativeAIEmbeddings = MagicMock
sys.modules["langchain_community.document_loaders"].WebBaseLoader  = MagicMock
sys.modules["langchain_text_splitters"].RecursiveCharacterTextSplitter = MagicMock

import os
os.environ["GEMINI_API_KEY"] = "test-gemini-key"
os.environ["DATABASE_URL"]   = "postgresql+asyncpg://user:pass@localhost/testdb"
os.environ["REDIS_URL"]      = "redis://localhost:6379"
os.environ["ADMIN_KEY"]      = "test-admin-secret"

import pytest


@pytest.fixture
def mock_redis():
    r        = AsyncMock()
    r.get    = AsyncMock(return_value=None)
    r.setex  = AsyncMock()
    r.delete = AsyncMock()
    r.aclose = AsyncMock()
    return r


@pytest.fixture
def mock_vector_store():
    vs                = MagicMock()
    vs.as_retriever   = MagicMock(return_value=AsyncMock())
    vs.aadd_documents = AsyncMock(return_value=None)
    return vs