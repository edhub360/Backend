from langchain_google_genai import ChatGoogleGenerativeAI   # only this changes
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import BaseMessage
from app.core.database import get_vector_store
from app.core.config import settings

SYSTEM_PROMPT = """You are a helpful customer support assistant for this website.
Answer ONLY based on the context provided below from the website content.
If the question is unrelated to the website or the context does not have
a relevant answer, politely say: "I can only answer questions related to this website."
Do not make up any information.

Context:
{context}
"""

def _format_docs(docs) -> str:
    return "\n\n".join(doc.page_content for doc in docs)

def get_llm() -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model=settings.CHAT_MODEL,
        google_api_key=settings.GEMINI_API_KEY,
        temperature=0,
    )

async def generate_reply(
    message: str,
    history: list[BaseMessage],
) -> tuple[str, list[str]]:
    retriever = get_vector_store().as_retriever(
        search_kwargs={"k": settings.RETRIEVER_TOP_K}
    )
    llm = get_llm()

    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="history"),
        ("human", "{question}"),
    ])

    docs = await retriever.ainvoke(message)
    context = _format_docs(docs)
    sources = list({
        doc.metadata.get("source", "")
        for doc in docs if doc.metadata.get("source")
    })

    chain = prompt | llm | StrOutputParser()

    reply = await chain.ainvoke({
        "context": context,
        "history": history,
        "question": message,
    })

    return reply, sources
