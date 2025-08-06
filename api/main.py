from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.cors import CORSMiddleware

from api.models.database import init_database
from api.routes import documents, classifiers, extractors, auth, service
from contextlib import asynccontextmanager
import os

# Development launch command using Ngrok
# ngrok http --subdomain=docprocesor-smolminds 8000

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

# Static files and templates
app.mount("/static", StaticFiles(directory="public"), name="static")
templates = Jinja2Templates(directory="templates")

allowed_origins = os.environ.get("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["authentication"])
app.include_router(documents.router, prefix="/documents", tags=["documents"])
app.include_router(classifiers.router, prefix="/classifiers", tags=["classifiers"])
app.include_router(extractors.router, prefix="/extractors", tags=["extractors"])
app.include_router(service.router, prefix="/service", tags=["service"])

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=os.environ.get("HOST", "0.0.0.0"),
        port=os.environ.get("PORT", "8000"),
        reload=os.environ.get("DEBUG", "false").lower() == "true"
    )