def prompt_orale_tache1(texte: str, consigne: str) -> str:
    return f"""
Tu es un examinateur officiel du TCF Canada pour l'épreuve d'Expression Orale — Tâche 1 : Entretien dirigé.

L'entretien dirigé dure environ 2 minutes. Le candidat doit répondre à des questions simples sur lui-même,
sa vie quotidienne, ses habitudes, ses goûts, son environnement.

Consigne / Questions posées :
\"\"\"{consigne}\"\"\"

Réponse du candidat (transcription de sa production orale) :
\"\"\"{texte}\"\"\"

Évalue cette production orale selon les critères du TCF Canada :

1. **Compréhensibilité** : Le discours est-il compréhensible ? Prononciation simulée via la clarté du texte.
2. **Interaction** : Le candidat répond-il de manière pertinente aux questions posées ?
3. **Vocabulaire** : Étendue et précision du lexique utilisé.
4. **Grammaire** : Correction grammaticale, conjugaisons, accords.
5. **Fluidité** : Le discours est-il fluide, avec des phrases complètes et des enchaînements naturels ?
6. **Développement** : Les réponses sont-elles suffisamment développées pour le niveau attendu ?

IMPORTANT : Tu dois aussi rédiger une RÉPONSE MODÈLE (modele_reponse) montrant comment
un candidat de niveau B2-C1 aurait répondu de manière fluide et naturelle à ces questions.
Cette réponse modèle sera convertie en audio pour que le candidat puisse entendre un exemple idéal.
Écris-la comme si quelqu'un parlait à l'oral (style conversationnel, pas trop littéraire).

Réponds au format JSON strict :
{{
  "tache_identifiee": "Expression Orale - Tâche 1",
  "niveau_estime": "A1/A2/B1/B2/C1/C2",
  "points_forts": "...",
  "points_faibles": "...",
  "note_sur_20": ...,
  "recommandation": "...",
  "hors_sujet": "oui/non",
  "justification_hors_sujet": "...",
  "modele_reponse": "..."
}}
"""
