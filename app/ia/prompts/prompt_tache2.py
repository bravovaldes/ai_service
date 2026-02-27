def prompt_tache2(texte: str, consigne: str) -> str:
    return f"""
Tu es un correcteur officiel du TCF Canada. Réponds **uniquement** par un JSON UTF-8 valide, sans ```json, sans texte avant ou après. Termine par le marqueur __END__JSON__.

❗️Tous les champs de texte (points forts, faibles, justification, etc.) doivent utiliser **du Markdown simple** pour la mise en forme :
- texte en **gras**
- listes avec `-`
- retours à la ligne (`\\n`)

Consigne donnée :
\"\"\"{consigne}\"\"\"

Voici le texte de l’utilisateur :
\"\"\"{texte}\"\"\"

Corrige ce texte selon les critères suivants :
1. Présence d’un titre, d’une accroche et d’une structure cohérente (chronologique ou thématique)
2. Expression claire des sentiments et avis personnels
3. Utilisation d’un style adapté (témoignage, blog, etc.)
4. Grammaire, orthographe, vocabulaire, connecteurs logiques

⚠️ Si le texte est incohérent, vide, ou uniquement composé de répétitions absurdes (ex. : "bonjour comment tu vas bonjour comment tu vas"), tu dois :
- mettre **"hors_sujet": "oui"**
- donner une **note faible (0 à 5 sur 20)** 
- expliquer clairement pourquoi dans la **justification_hors_sujet**
- ignorer les compliments inutiles

Réponds au format JSON strict :

{{
  "tache_identifiee": "Tâche 2",
  "niveau_estime": "B1",
  "points_forts": "**Bonne structure globale.**\\n- Titre présent\\n- Style personnel adapté",
  "points_faibles": "**Problèmes de grammaire.**\\n- Erreurs d'accord\\n- Style parfois familier",
  "note_sur_20": 13,
  "recommandation": "**Ajoutez plus d’exemples.**\\nClarifiez certains passages flous.",
  "hors_sujet": "non",
  "justification_hors_sujet": "**Le texte est bien en lien avec la consigne.**"
}}
__END__JSON__
"""
