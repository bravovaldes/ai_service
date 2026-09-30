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

    # Mesures issues de l'audio, quand le client en a.
    #
    # La tâche 2 est un dialogue : le candidat parle en plusieurs tours, et
    # aucun fichier unique ne couvre l'épreuve. Les mesures sont donc
    # calculées tour par tour par /tache2/tour, agrégées par le client, puis
    # renvoyées ici — sans quoi la correction d'une épreuve ORALE ne dirait
    # rien du débit ni des hésitations.
    analyse_audio: Optional[dict] = None

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


class Tache2TourResponse(BaseModel):
    """Un tour de dialogue, rendu en une seule fois."""

    transcription: str
    reponse_examinateur: str

    # L'examinateur PARLE. Une épreuve d'interaction orale dont on lit les
    # répliques n'entraîne pas à l'épreuve : il faut comprendre à l'oreille,
    # à la vitesse de l'autre, sans pouvoir relire.
    audio_url: Optional[str] = None

    analyse_audio: Optional[dict] = None
    erreur: Optional[str] = None
