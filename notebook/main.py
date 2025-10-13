from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
import uvicorn
from utils.logging import setup_logging
from routes import notebooks, sources, embeddings

app = FastAPI(title="NotebookLM Backend", version="1.0.0")

# CORS config as needed
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # limit in production!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

setup_logging(app)

app.include_router(notebooks.router, prefix="/api/notebooks")
app.include_router(sources.router, prefix="/api/sources")
app.include_router(embeddings.router, prefix="/api/embeddings")

@app.get("/")
async def root():
    return {"msg": "NotebookLM Backend running"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)
