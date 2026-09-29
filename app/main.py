from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

# Import des routers
from app.api.routes_feedback import router as feedback_router
from app.api.expression_routes import router as expression_router
from app.api.centres_routes import router as centres_router
from app.api.orale_routes import router as orale_router

app = FastAPI(title="TCF Express API")


@app.get("/health", tags=["service"])
def health() -> dict:
    """Sonde de sante pour Render.

    Le service n'en avait aucune : Render ne pouvait donc pas savoir s'il
    etait vivant, et une panne passait inapercue jusqu'a ce qu'un
    utilisateur s'en plaigne.

    On verifie la presence des cles SANS les utiliser : un appel reel a
    Claude a chaque sonde coûterait cher et serait lent.
    """
    import os

    return {
        "ok": True,
        "anthropic": bool(os.getenv("ANTHROPIC_API_KEY")),
        "firebase": bool(os.getenv("FIREBASE_SERVICE_ACCOUNT")),
        "tts": bool(os.getenv("GOOGLE_CREDENTIALS_JSON")),
    }


@app.get("/", include_in_schema=False)
def racine() -> dict:
    return {"service": "TCF Express API", "docs": "/docs", "sante": "/health"}

# Router Feedback
app.include_router(feedback_router, prefix="/feedback")

# Router Centres TCF
app.include_router(centres_router)

# Router Expression écrite
app.include_router(expression_router)

# Router Expression orale
app.include_router(orale_router)
