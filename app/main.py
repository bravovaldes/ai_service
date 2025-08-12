from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

# 🟢 Import des routers
from app.api.routes_feedback import router as feedback_router
from app.api.expression_routes import router as expression_router
from app.api.centres_routes import router as centres_router
app = FastAPI(title="TCF Express API")

# 🟩 Router Feedback
app.include_router(feedback_router, prefix="/feedback")

app.include_router(centres_router)
# 🟦 Router Expression (ex. expression écrite/orale)
app.include_router(expression_router)
