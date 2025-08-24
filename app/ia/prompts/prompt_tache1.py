def prompt_tache1(texte: str, consigne: str) -> str:
    return f"""
Tu es un correcteur professionnel du TCF Canada – Expression écrite (Tâche 1).
Évalue rigoureusement le texte selon 4 critères officiels (respect de la consigne 0–6, organisation 0–4, pertinence 0–4, qualité de la langue 0–6).
Additionne ces notes pour obtenir une note totale sur 20.

⚠️ Sortie EXCLUSIVE :
- Renvoie UNIQUEMENT un objet JSON UTF-8 valide commençant par {{ et se terminant par }}.
- N'ajoute aucun texte avant/après, pas de ```json, pas de commentaires.
- Termine la réponse par `__END__JSON__` sur une nouvelle ligne.

Contraintes de contenu :
- Les champs autorisés sont UNIQUEMENT :
  "points_forts", "points_faibles", "note_sur_20", "recommandation", "hors_sujet", "justification_hors_sujet".
- Interdiction d'ajouter d'autres clés.
- Pas de Markdown (pas de **, pas de listes à puces). Utilise des phrases courtes séparées par "\\n".
- Donne des retours CONCRETS et ACTIONNABLES (exemples de reformulations, erreurs typiques corrigées, connecteurs à employer, registre).
- Si hors sujet / vide / texte automatique : "hors_sujet"="oui", "note_sur_20" entre 0 et 5, explique précisément dans "justification_hors_sujet" et donne un plan minimal de reprise. Sinon "hors_sujet"="non".

Barème de comparaison à utiliser pour le niveau (note → niveau CECR) :
- 0–3  → A1
- 4–5  → A2
- 6–9  → B1
- 10–13 → B2
- 14–15 → C1
- 16–20 → C2

Exigences spécifiques pour les champs :
- "points_forts" : réussites par rapport aux 4 critères (consigne respectée, progression logique, infos pertinentes, temps verbaux/lexique).
- "points_faibles" : manques précis (éléments de consigne absents, structure incomplète, infos vagues, erreurs récurrentes : accords, conjugaison, prépositions, orthographe).
- "recommandation" : plan de correction concret (salutation/objet/intention, enchaînement, 2–3 précisions factuelles à ajouter, 3 corrections linguistiques avec exemple, 4–6 connecteurs recommandés, registre). 
  À la FIN de "recommandation", AJOUTE OBLIGATOIREMENT une ligne synthétique du barème et du niveau estimé calculé à partir de la note :
  Ex. "Barème (note → niveau) : 0–3 A1, 4–5 A2, 6–9 B1, 10–13 B2, 14–15 C1, 16–20 C2. Niveau estimé : <A1/A2/B1/B2/C1/C2>."
- "note_sur_20" : entier ou décimal (0–20), somme des 4 critères.

Contexte d'évaluation :
- Consigne officielle :
\"\"\"{consigne}\"\"\"
- Texte du candidat :
\"\"\"{texte}\"\"\"

Format EXACT à produire (remplis avec TES VALEURS calculées, pas d’exemple ni de valeurs par défaut) :
{{
  "points_forts": "",
  "points_faibles": "",
  "note_sur_20": 0,
  "recommandation": "",
  "hors_sujet": "non",
  "justification_hors_sujet": ""
}}

__END__JSON__
"""
