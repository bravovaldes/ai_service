from fastapi import APIRouter
from app.schemas.expression_schema import (
    ExpressionRequestTache1,
    ExpressionRequestTache2,
    ExpressionRequestTache3
)
from app.ia.correcteurs import correcteur_tache1, correcteur_tache2, correcteur_tache3

router = APIRouter(prefix="/expression", tags=["expression"])

@router.post("/tache1")
async def analyser_tache1(data: ExpressionRequestTache1):
    return correcteur_tache1.corriger_tache1(data.texte, data.consigne)

@router.post("/tache2")
async def analyser_tache2(data: ExpressionRequestTache2):
    return correcteur_tache2.corriger_tache2(data.texte, data.consigne)

@router.post("/tache3")
async def analyser_tache3(data: ExpressionRequestTache3):
    return correcteur_tache3.corriger_tache3(
        data.texte,
        data.document1,
        data.document2,
        data.consigne
    )
