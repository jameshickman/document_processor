from fastapi import FastAPI
from .models import init_database
from .routes import documents, classifiers, extractors
import os

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    init_database(
        db_user=os.environ.get("POSTGRES_USER", "user"),
        db_pass=os.environ.get("POSTGRES_PASSWORD", "password"),
        db_host=os.environ.get("POSTGRES_HOST", "localhost"),
        db_port=int(os.environ.get("POSTGRES_PORT", 5432)),
        db_name=os.environ.get("POSTGRES_DB", "database"),
    )

app.include_router(documents.router, prefix="/documents", tags=["documents"])
app.include_router(classifiers.router, prefix="/classifiers", tags=["classifiers"])
app.include_router(extractors.router, prefix="/extractors", tags=["extractors"])

@app.get("/")
async def root():
    return {"message": "Classifier and Extractor API"}