from pydantic import BaseModel
from typing import List, Optional

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

# Réponse Expression Orale (avec audio modèle ElevenLabs)
class ExpressionOraleResponse(BaseModel):
    tache_identifiee: str
    niveau_estime: str
    points_forts: str
    points_faibles: str
    note_sur_20: float
    recommandation: str
    hors_sujet: Optional[str] = None
    justification_hors_sujet: Optional[str] = None
    modele_reponse: Optional[str] = None
    audio_modele_url: Optional[str] = None


# ─── Chat interactif Tâche 2 ────────────────────────────────

class ChatMessage(BaseModel):
    role: str       # "examinateur" | "candidat"
    content: str

class Tache2ChatRequest(BaseModel):
    scenario: str
    role_examinateur: str
    consigne: str
    historique: List[ChatMessage]
    message_candidat: str

class Tache2ChatResponse(BaseModel):
    reponse_examinateur: str
