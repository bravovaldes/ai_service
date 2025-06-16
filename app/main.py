from fastapi import FastAPI
from app.api.routes_feedback import router as feedback_router
from app.api import routes_tts

app = FastAPI()
app.include_router(feedback_router, prefix="/feedback")
app.include_router(routes_tts.router, prefix="/tts", tags=["Text-to-Speech"])