from app.ia.prompts.calibrage_ecrit import longueur


def prompt_tache1(texte: str, consigne: str) -> str:
    return f"""
Tu es un correcteur professionnel du TCF Canada – Expression écrite (Tâche 1).
Corrige le texte du candidat **naturellement** et **factuellement**, 
en appliquant **strictement** les critères officiels du TCF.

{longueur(60, 120)}


---

📌 **Consigne officielle** :
\"\"\"{consigne}\"\"\"

✍️ **Texte du candidat** :
\"\"\"{texte}\"\"\"



__END__JSON__
"""
