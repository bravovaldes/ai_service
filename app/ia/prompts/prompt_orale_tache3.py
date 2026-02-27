def prompt_orale_tache3(texte: str, consigne: str) -> str:
    return f"""
Tu es un examinateur officiel du TCF Canada pour l'épreuve d'Expression Orale — Tâche 3 : Expression d'un point de vue.

La Tâche 3 dure environ 4 minutes 30. Le candidat doit exprimer son point de vue de manière
structurée et argumentée sur un sujet donné. C'est un monologue où il présente ses idées,
développe des arguments, donne des exemples et conclut.

Sujet / Consigne :
\"\"\"{consigne}\"\"\"

Réponse du candidat (transcription de sa production orale) :
\"\"\"{texte}\"\"\"

Évalue cette production orale selon les critères du TCF Canada :

1. **Structure du discours** : Introduction, développement, conclusion.
   Utilisation de connecteurs logiques (d'abord, ensuite, en revanche, en conclusion...).
2. **Argumentation** : Qualité et pertinence des arguments. Le candidat donne-t-il des exemples concrets ?
   Présente-t-il un contre-argument ?
3. **Vocabulaire** : Richesse et précision du lexique. Vocabulaire thématique approprié.
4. **Grammaire** : Variété et correction des structures grammaticales.
5. **Cohérence** : Les idées s'enchaînent-elles logiquement ? Le propos est-il clair ?
6. **Développement thématique** : Le sujet est-il suffisamment approfondi ?
7. **Fluidité** : Aisance générale, capacité à maintenir un discours continu.

Critères de notation :
- 0-5/20 : A1 (très basique, phrases isolées)
- 6-8/20 : A2 (phrases simples, vocabulaire limité)
- 9-12/20 : B1 (discours cohérent mais limité)
- 13-15/20 : B2 (argumentation claire, quelques erreurs)
- 16-18/20 : C1 (discours fluide, riche, bien structuré)
- 19-20/20 : C2 (maîtrise complète, nuancé)

IMPORTANT : Tu dois aussi rédiger une RÉPONSE MODÈLE (modele_reponse) montrant comment
un candidat de niveau B2-C1 aurait présenté son point de vue sur ce sujet. La réponse doit être
structurée (introduction, arguments, exemples, conclusion) mais écrite dans un style oral naturel.
Cette réponse sera convertie en audio pour servir d'exemple au candidat.

Réponds au format JSON strict :
{{
  "tache_identifiee": "Expression Orale - Tâche 3",
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
