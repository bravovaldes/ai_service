from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import List
from app.core.azure_speech import synthesize_speech

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
        path = synthesize_speech(
            intro=req.intro,
            question=req.question,
            options=req.options,
            voice=req.voice,
            format=req.format
        )
        relative_path = str(path).replace("\\", "/")
        full_url = request.base_url._url + relative_path
        return {"audio_url": full_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
