def prompt_tache3(texte: str, document1: str, document2: str, consigne: str) -> str:
    return f"""
Tu es un correcteur officiel du TCF Canada. Réponds uniquement par un JSON UTF-8 valide, sans ```json, sans texte avant ou après. Termine par le marqueur __END__JSON__.

❗️Tous les champs de texte (points forts, faibles, justification, etc.) doivent utiliser du Markdown simple :
- texte en **gras** (avec modération)
- listes avec `-`
- retours à la ligne (`\\n`)

Voici la consigne :
\"\"\"{consigne}\"\"\"

Document 1 :
\"\"\"{document1}\"\"\"

Document 2 :
\"\"\"{document2}\"\"\"

Texte du candidat :
\"\"\"{texte}\"\"\"

Corrige ce texte selon les critères suivants :
1. Présentation des deux avis (40–60 mots)
2. Opinion personnelle claire (80–120 mots)
3. Arguments personnels, contre-argument, structure logique
4. Orthographe, connecteurs, richesse du vocabulaire

⚠️ Si le texte est vide, incohérent ou composé de répétitions absurdes (ex. : "bonjour comment tu vas bonjour comment tu vas"), tu dois :
- mettre "hors_sujet": "oui"
- attribuer une note très faible (0 à 5 sur 20)
- expliquer clairement pourquoi dans la justification_hors_sujet
- ne pas faire de compliments non mérités

✅ Dans le champ `recommandation`, donne des conseils pratiques directement liés au sujet :
- améliorer un argument déjà mentionné
- proposer des exemples concrets
- clarifier une idée
- utiliser un vocabulaire plus précis

Réponds au format JSON strict :

{{
  "tache_identifiee": "Offrir un animal de compagnie à un enfant",
  "niveau_estime": "Satisfaisant",
  "points_forts": "- Opinion personnelle claire\\n- Arguments pertinents",
  "points_faibles": "- Manque de présentation des deux points de vue\\n- Arguments peu développés",
  "note_sur_20": 12,
  "recommandation": "- Ajoutez un exemple personnel lié à un animal.\\n- Expliquez les responsabilités qu’un enfant peut apprendre.",
  "hors_sujet": "non",
  "justification_hors_sujet": "Le texte est en lien avec la consigne."
}}
__END__JSON__\n"""
