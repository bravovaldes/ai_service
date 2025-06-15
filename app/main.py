from fastapi import FastAPI
from app.api.routes_feedback import router as feedback_router

app = FastAPI()
app.include_router(feedback_router, prefix="/feedback")
