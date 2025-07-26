from openai import OpenAI
import json
from app.ia.prompts.prompt_tache3 import prompt_tache3
import os
from dotenv import load_dotenv

load_dotenv()

# ✅ Création du client OpenAI avec la clé API
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def corriger_tache3(texte: str, document1: str, document2: str, consigne: str) -> dict:
    prompt = prompt_tache3(texte, document1, document2, consigne)

    # ✅ Nouvelle façon d'appeler le modèle
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=0.7
    )

    # ✅ Accès au texte généré
    result = response.choices[0].message.content

    try:
        return json.loads(result)
    except json.JSONDecodeError:
        return {
            "tache_identifiee": "Tâche 3",
            "niveau_estime": "Erreur",
            "points_forts": "Format JSON incorrect",
            "points_faibles": "Le modèle n’a pas respecté le format attendu.",
            "note_sur_20": 0,
            "recommandation": "Réessayez avec un texte plus clair.",
            "hors_sujet": "oui",
            "justification_hors_sujet": "Réponse illisible par le système."
        }
