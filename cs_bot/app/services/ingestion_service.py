import json
from pathlib import Path
from langchain_community.document_loaders import WebBaseLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from app.core.database import get_vector_store


async def ingest_urls(urls: list[str]) -> int:
    loader = WebBaseLoader(web_paths=urls)
    docs = loader.load()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        separators=["\n\n", "\n", ".", " "],
    )
    chunks = splitter.split_documents(docs)

    for chunk in chunks:
        chunk.metadata["source"] = chunk.metadata.get("source", "")

    get_vector_store().add_documents(chunks)
    return len(chunks)


# Added — ingest from local JSON file
async def ingest_json(file_path: str = "data/website_content.json") -> int:
    raw = json.loads(Path(file_path).read_text())

    docs = [
        Document(
            page_content=item["content"],
            metadata={"source": item["page"]}
        )
        for item in raw
    ]

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        separators=["\n\n", "\n", ".", " "],
    )
    chunks = splitter.split_documents(docs)
    get_vector_store().add_documents(chunks)
    return len(chunks)
