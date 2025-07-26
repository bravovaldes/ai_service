from fastapi import FastAPI
from app.api.routes_feedback import router as feedback_router
from app.api import routes_tts
from app.api.expression_routes import router as expression_router
from fastapi.staticfiles import StaticFiles
app = FastAPI()
app.include_router(feedback_router, prefix="/feedback")
# 🟩 Montre les fichiers audios générés
app.mount("/static", StaticFiles(directory="static"), name="static")

# 🟦 Router pour Text-to-Speech
app.include_router(routes_tts.router, prefix="/tts", tags=["Text-to-Speech"])
app.include_router(expression_router)