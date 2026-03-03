def prompt_tache2(texte: str, consigne: str) -> str:
    return f"""
Tu es un correcteur professionnel du TCF Canada – Expression écrite (Tâche 2 : Argumentation).
Corrige le texte du candidat **naturellement** et **factuellement**, 
en appliquant **strictement** les critères officiels du TCF.

⚠️ Très important :
- Si le texte est **bien structuré, clair, complet et argumenté**, **n’hésite pas à donner un C1 ou un C2** selon le barème.
- Le champ "niveau_estime" doit TOUJOURS être calculé uniquement à partir de la note finale selon ce barème :

- 0 → 3  = A1  
- 4 → 5  = A2  
- 6 → 9  = B1  
- 10 → 13 = B2  
- 14 → 15 = C1  
- 16 → 20 = C2

Réponds **uniquement** par un **JSON UTF-8 valide**, sans texte avant ou après, pas de ```json.
Termine toujours la réponse par `__END__JSON__`.

---

📌 **Consigne officielle à respecter** :
\"\"\"{consigne}\"\"\"

✍️ **Texte du candidat** :
\"\"\"{texte}\"\"\"

---

### ✅ Exigences pour les champs JSON :

- **"points_forts"** → forces précises : respect de la consigne, bonne organisation, arguments pertinents, bons connecteurs, registre adapté.  
- **"points_faibles"** → faiblesses concrètes : arguments manquants, exemples insuffisants, répétitions, structure perfectible, fautes récurrentes.  
- **"recommandation"** → message **court et général** (1 ou 2 phrases maximum).  
  Exemple :  
  > "Développez un peu plus vos arguments et ajoutez des exemples concrets pour renforcer l'impact."  
- **"note_sur_20"** → note finale stricte (0–20).  
- **"niveau_estime"** → uniquement le niveau CECRL exact selon le barème.  
- **"hors_sujet"** → `"oui"` si le texte est vide, hors sujet ou incohérent, sinon `"non"`.
- **"justification_hors_sujet"** → rempli uniquement si `"hors_sujet" = "oui"` et expliquer **précisément** pourquoi.
- **"modele_reponse"** → Un exemple court de texte argumentatif bien structuré qui aurait obtenu une bonne note (B2-C1) pour cette consigne (130–160 mots, sans titre, sans commentaire, juste le texte).

---

### 🧾 Format strict JSON attendu :

{{
  "niveau_estime": "",
  "points_forts": "",
  "points_faibles": "",
  "note_sur_20": 0,
  "recommandation": "",
  "hors_sujet": "",
  "justification_hors_sujet": "",
  "modele_reponse": ""
}}

⚠️ Règles importantes :
- Si le texte est **complet et bien argumenté**, **n’hésite pas à attribuer C1 ou C2**.
- `recommandation` doit être **courte et générale**.
- Pas de gras, pas de Markdown, pas de listes.
- Respecte **strictement** cet ordre et ces clés.

__END__JSON__
"""
