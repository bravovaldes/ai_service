from app.ia.prompts.calibrage_ecrit import longueur


def prompt_tache2(texte: str, consigne: str) -> str:
    return f"""
Tu es un correcteur professionnel du TCF Canada – Expression écrite (Tâche 2 : Argumentation).
Corrige le texte du candidat **naturellement** et **factuellement**, 
en appliquant **strictement** les critères officiels du TCF.

{longueur(120, 150)}


---

📌 **Consigne officielle à respecter** :
\"\"\"{consigne}\"\"\"

✍️ **Texte du candidat** :
\"\"\"{texte}\"\"\"



__END__JSON__
"""
