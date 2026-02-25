from langchain_community.document_loaders import WebBaseLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
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

    # Tag each chunk with its source URL
    for chunk in chunks:
        chunk.metadata["source"] = chunk.metadata.get("source", "")

    get_vector_store().add_documents(chunks)

    return len(chunks)
