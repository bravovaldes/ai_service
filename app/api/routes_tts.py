from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import List
from app.core.azure_speech import synthesize_question_format
from firebase_utils import upload_audio_to_firebase
import os

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

        # Upload vers Firebase Storage
        firebase_url = upload_audio_to_firebase(path)

        # Supprime le fichier local
        os.remove(path)

        return {"audio_url": firebase_url}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
