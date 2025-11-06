from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes.upload import router as upload_router
from app.routes.chat import router as chat_router

app = FastAPI(
    title="SmartStudy API",
    description="AI Chat Application with General and RAG modes",
    version="1.0.0"
)

# CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://staging.alconsultingltd.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(upload_router, prefix="/upload", tags=["upload"])
app.include_router(chat_router, prefix="/chat", tags=["chat"])

@app.get("/")
async def root():
    return {"message": "SmartStudy API is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
