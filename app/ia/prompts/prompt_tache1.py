def prompt_tache1(texte: str, consigne: str) -> str:
    return f"""
Tu es un correcteur d’expression écrite pour le TCF.

Consigne de l’exercice :
{consigne}

Texte de l'utilisateur :
{texte}

Corrige ce texte selon les critères du TCF : tâche identifiée, niveau estimé (A1 à C2), points forts, points faibles, note sur 20, recommandation, vérification du hors sujet.

Réponds au format JSON strict :
{{
  "tache_identifiee": "...",
  "niveau_estime": "...",
  "points_forts": "...",
  "points_faibles": "...",
  "note_sur_20": ...,
  "recommandation": "...",
  "hors_sujet": "oui/non",
  "justification_hors_sujet": "..."
}}
"""
