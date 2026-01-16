from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.cors import CORSMiddleware

from api.models.database import init_database
from api.routes import documents, classifiers, extractors, auth, service, api_config, account, llm_models
from api.routes import reporting
from api.util.files_abstraction import init_filesystem_from_env
from contextlib import asynccontextmanager
import os

# Development launch command using Ngrok
# ngrok http --subdomain=docprocessor-smolminds 8000

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
    # Initialize filesystem backend
    init_filesystem_from_env()
    yield
    # Shutdown: Cleanup code can go here if needed

app = FastAPI(lifespan=lifespan)

# Static files and templates
app.mount("/static", StaticFiles(directory="api/public"), name="static")
templates = Jinja2Templates(directory="api/templates")

allowed_origins = os.environ.get("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["authentication"])
app.include_router(account.router, prefix="/account", tags=["account"])
app.include_router(documents.router, prefix="/documents", tags=["documents"])
app.include_router(classifiers.router, prefix="/classifiers", tags=["classifiers"])
app.include_router(extractors.router, prefix="/extractors", tags=["extractors"])
app.include_router(llm_models.router, prefix="/llm_models", tags=["llm_models"])
app.include_router(service.router, prefix="/service", tags=["service"])
app.include_router(api_config.router, prefix="/api_config", tags=["api_config"])
app.include_router(reporting.router, prefix="/reporting", tags=["reporting"])

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