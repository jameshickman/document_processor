import logging
import os

from fastapi import FastAPI
from pydantic import BaseModel




app = FastAPI()

class ExtractionAnswer(BaseModel):
    confidence: float
    found: bool
    explanation: str
    extracted_data: dict[str, str]

class ExtractionPayload(BaseModel):
    result: ExtractionAnswer
    file_name: str
    document_id: int
    csrf_token: str


@app.post('/webhook')
async def webhook(payload: ExtractionPayload):
    print(payload)
    logging.info(f"Webhook received: {payload}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "webhook_tester:app",
        host=os.environ.get("HOST", "0.0.0.0"),
        port=os.environ.get("PORT", "8001"),
        reload=os.environ.get("DEBUG", "false").lower() == "true"
    )