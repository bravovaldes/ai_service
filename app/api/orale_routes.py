from fastapi import APIRouter
from app.schemas.expression_schema import (
    ExpressionRequestTache1,
    ExpressionRequestTache2,
    ExpressionOraleResponse
)
from app.ia.correcteurs import correcteur_orale_tache1, correcteur_orale_tache2, correcteur_orale_tache3
from app.core.elevenlabs_tts import synthesize_with_elevenlabs
import os

router = APIRouter(prefix="/expression-orale", tags=["expression-orale"])

def _add_audio_modele(result: dict) -> dict:
    """Génère l'audio du modèle de réponse via ElevenLabs si disponible."""
    modele = result.get("modele_reponse", "")
    if modele and os.getenv("ELEVENLABS_API_KEY"):
        try:
            audio_url = synthesize_with_elevenlabs(modele)
            result["audio_modele_url"] = audio_url
        except Exception as e:
            result["audio_modele_url"] = None
            print(f"⚠️ ElevenLabs TTS error: {e}")
    else:
        result["audio_modele_url"] = None
    return result

@router.post("/tache1", response_model=ExpressionOraleResponse)
def analyser_orale_tache1(data: ExpressionRequestTache1):
    result = correcteur_orale_tache1.corriger_orale_tache1(data.texte, data.consigne)
    return _add_audio_modele(result)

@router.post("/tache2", response_model=ExpressionOraleResponse)
def analyser_orale_tache2(data: ExpressionRequestTache2):
    result = correcteur_orale_tache2.corriger_orale_tache2(data.texte, data.consigne)
    return _add_audio_modele(result)

@router.post("/tache3", response_model=ExpressionOraleResponse)
def analyser_orale_tache3(data: ExpressionRequestTache2):
    result = correcteur_orale_tache3.corriger_orale_tache3(data.texte, data.consigne)
    return _add_audio_modele(result)
