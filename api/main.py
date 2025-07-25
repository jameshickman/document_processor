from fastapi import FastAPI
from api.models.database import init_database
from api.routes import documents, classifiers, extractors, auth
from contextlib import asynccontextmanager
import os

@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Startup: Initialize database
    init_database(
        db_user=os.environ.get("POSTGRES_USER", "user"),
        db_pass=os.environ.get("POSTGRES_PASSWORD", "password"),
        db_host=os.environ.get("POSTGRES_HOST", "localhost"),
        db_port=int(os.environ.get("POSTGRES_PORT", 5432)),
        db_name=os.environ.get("POSTGRES_DB", "database"),
    )
    yield
    # Shutdown: Cleanup code can go here if needed

app = FastAPI(lifespan=lifespan)

app.include_router(auth.router, prefix="/auth", tags=["authentication"])
app.include_router(documents.router, prefix="/documents", tags=["documents"])
app.include_router(classifiers.router, prefix="/classifiers", tags=["classifiers"])
app.include_router(extractors.router, prefix="/extractors", tags=["extractors"])

@app.get("/")
async def root():
    return {"message": "Classifier and Extractor API"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=os.environ.get("HOST", "0.0.0.0"),
        port=os.environ.get("PORT", "8000"),
        reload=os.environ.get("DEBUG", "false").lower() == "true"
    )