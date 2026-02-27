from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import List
from app.core.azure_speech import synthesize_speech
from firebase_utils import upload_audio_to_firebase
import os

router = APIRouter()

class TTSRequest(BaseModel):
    intro: str
    question: str
    options: List[str]
    voice: str = "fr-FR-HenriNeural"
    format: str = "audio-16khz-128kbitrate-mono-mp3"

@router.post("/generate")
def generate_audio(req: TTSRequest, request: Request):
    try:
        # 1. Génère le fichier local
        local_path = synthesize_speech(
            intro=req.intro,
            question=req.question,
            options=req.options,
            voice=req.voice,
            format=req.format
        )

        # 2. Upload vers Firebase Storage
        firebase_url = upload_audio_to_firebase(local_path)

        # 3. Optionnel : supprime le fichier local
        os.remove(local_path)

        # 4. Retourne l’URL publique
        return {"audio_url": firebase_url}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
