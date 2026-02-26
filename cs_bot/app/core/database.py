from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_postgres import PGVector
from app.core.config import settings

embeddings: GoogleGenerativeAIEmbeddings = None
vector_store: PGVector = None

def init_vector_store():
    global embeddings, vector_store

    embeddings = GoogleGenerativeAIEmbeddings(
        model=settings.EMBEDDING_MODEL,          # models/gemini-embedding-001
        google_api_key=settings.GEMINI_API_KEY,
        task_type="semantic_similarity",         # ✅ matches your notebook service
    )
    vector_store = PGVector(
        embeddings=embeddings,
        collection_name=settings.VECTOR_COLLECTION,
        connection=settings.PGVECTOR_URL,
        use_jsonb=True,
        create_extension=False,
        pre_delete_collection=False,
        async_mode=True,
        engine_args={
            "connect_args": {
                "options": "-csearch_path=stud_hub_schema,public"
            }
        }
    )

def get_vector_store() -> PGVector:
    return vector_store
