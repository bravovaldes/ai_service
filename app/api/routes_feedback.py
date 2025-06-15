from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

class FeedbackRequest(BaseModel):
    texte: str
    niveau: str

class FeedbackResponse(BaseModel):
    niveau_estimé: str

@router.post("/ecriture", response_model=FeedbackResponse)
async def feedback(request: FeedbackRequest):
    return {"niveau_estimé": request.niveau}
