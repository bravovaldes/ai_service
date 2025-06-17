def prompt_tache3(texte: str, document1: str, document2: str, consigne: str) -> str:
    return f"""
Tu es un correcteur officiel du TCF Canada. Le candidat a produit un texte de Tâche 3 : Texte argumentatif.

Consigne :
{consigne}

Documents :
 Document 1 :
\"\"\"{document1}\"\"\"

 Document 2 :
\"\"\"{document2}\"\"\"

Voici le texte produit par le candidat :
------------------------
{texte}
------------------------

Corrige ce texte selon les critères suivants :
1. Présentation objective des deux avis (40–60 mots)
2. Expression claire de l’opinion personnelle (80–120 mots)
3. Arguments personnels, contre-argument, structure logique
4. Orthographe, connecteurs logiques, richesse du vocabulaire

Réponds au format JSON strict :
{{
  "tache_identifiee": "Tâche 3",
  "niveau_estime": "...",
  "points_forts": "...",
  "points_faibles": "...",
  "note_sur_20": ...,
  "recommandation": "...",
  "hors_sujet": "oui/non",
  "justification_hors_sujet": "..."
}}
"""
