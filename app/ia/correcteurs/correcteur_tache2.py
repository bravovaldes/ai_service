from openai import OpenAI
import json
import os
from dotenv import load_dotenv
from app.ia.prompts.prompt_tache2 import prompt_tache2

load_dotenv()  # Charge les variables d’environnement
api_key = os.getenv("OPENAI_API_KEY")

# ✅ Instanciation du client OpenAI
client = OpenAI(api_key=api_key)

def corriger_tache2(texte: str, consigne: str) -> dict:
    if not api_key:
        return {
            "tache_identifiee": "Tâche 2",
            "niveau_estime": "Erreur",
            "points_forts": "Clé API manquante",
            "points_faibles": "La variable d’environnement OPENAI_API_KEY n’a pas été chargée.",
            "note_sur_20": 0,
            "recommandation": "Vérifiez votre fichier .env.",
            "hors_sujet": "oui",
            "justification_hors_sujet": "Erreur d’authentification."
        }

    prompt = prompt_tache2(texte, consigne)
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        result = response.choices[0].message.content
        return json.loads(result)
    except Exception as e:
        return {
            "tache_identifiee": "Tâche 2",
            "niveau_estime": "Erreur",
            "points_forts": "Exception levée",
            "points_faibles": str(e),
            "note_sur_20": 0,
            "recommandation": "Vérifiez les erreurs dans votre console.",
            "hors_sujet": "oui",
            "justification_hors_sujet": "Erreur interne lors du traitement."
        }
