from fastapi import FastAPI
from app.routes_importer import router

app = FastAPI(title="Course Importer Service")

app.include_router(router)

@app.get("/health")
def health():
    return {"status": "ok", "service": "course-importer"}