from pydantic import BaseModel
from typing import Optional

# Requête Tâche 1
class ExpressionRequestTache1(BaseModel):
    texte: str
    consigne: str

# Requête Tâche 2
class ExpressionRequestTache2(BaseModel):
    texte: str
    consigne: str

# Requête Tâche 3
class ExpressionRequestTache3(BaseModel):
    texte: str
    consigne: str
    document1: str
    document2: str

# Réponse commune pour toutes les tâches
class ExpressionResponse(BaseModel):
    tache_identifiee: str
    niveau_estime: str
    points_forts: str
    points_faibles: str
    note_sur_20: float
    recommandation: str
    hors_sujet: Optional[str] = None
    justification_hors_sujet: Optional[str] = None
