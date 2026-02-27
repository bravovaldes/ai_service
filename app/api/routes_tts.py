from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import List
from app.core.azure_speech import synthesize_question_format

router = APIRouter()

class QuestionRequest(BaseModel):
    question: str
    options: List[str]

@router.post("/generate-question")
def generate_question(req: QuestionRequest, request: Request):
    try:
        path = synthesize_question_format(
            question_text=req.question,
            options=req.options
        )

        # Retourne le chemin audio local
        base_url = str(request.base_url).rstrip("/")
        audio_url = f"{base_url}/{path}"
        return {"audio_url": audio_url}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
