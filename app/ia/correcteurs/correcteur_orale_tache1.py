import json
import os
from openai import OpenAI
from dotenv import load_dotenv
from app.ia.prompts.prompt_orale_tache1 import prompt_orale_tache1

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def corriger_orale_tache1(texte: str, consigne: str) -> dict:
    prompt = prompt_orale_tache1(texte, consigne)

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Tu es un examinateur du TCF Canada pour l'expression orale. Tu réponds en JSON structuré."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )

        result = response.choices[0].message.content.strip()
        return json.loads(result)

    except json.JSONDecodeError:
        return {
            "tache_identifiee": "Expression Orale - Tâche 1",
            "niveau_estime": "Erreur",
            "points_forts": "Format JSON incorrect",
            "points_faibles": "Le modèle n'a pas respecté le format attendu.",
            "note_sur_20": 0,
            "recommandation": "Réessayez avec un texte plus clair.",
            "hors_sujet": "oui",
            "justification_hors_sujet": "Réponse illisible par le système."
        }

    except Exception as e:
        return {
            "tache_identifiee": "Expression Orale - Tâche 1",
            "niveau_estime": "Erreur API",
            "points_forts": "Aucun",
            "points_faibles": str(e),
            "note_sur_20": 0,
            "recommandation": "Problème avec la requête API.",
            "hors_sujet": "oui",
            "justification_hors_sujet": "Erreur technique."
        }
