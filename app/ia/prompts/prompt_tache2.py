def prompt_tache2(texte: str, consigne: str) -> str:
    return f"""
Tu es un correcteur officiel du TCF Canada. Le candidat a produit un texte pour la Tâche 2 : écrire un article ou témoignage.

Consigne donnée :
\"\"\"{consigne}\"\"\"

Voici le texte de l’utilisateur :
\"\"\"{texte}\"\"\"

Ta mission est de corriger ce texte selon les critères suivants :
1. Présence d’un titre, d’une accroche et d’une structure cohérente (chronologique ou thématique)
2. Expression claire des sentiments et avis personnels
3. Utilisation d’un style adapté (témoignage, blog, etc.)
4. Grammaire, orthographe, vocabulaire, connecteurs logiques

Réponds au format JSON strict :
{{
  "tache_identifiee": "Tâche 2",
  "niveau_estime": "...",
  "points_forts": "...",
  "points_faibles": "...",
  "note_sur_20": ...,
  "recommandation": "...",
  "hors_sujet": "oui/non",
  "justification_hors_sujet": "..."
}}
"""
