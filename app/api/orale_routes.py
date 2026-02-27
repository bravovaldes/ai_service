import os
import json
import time
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from app.schemas.expression_schema import ExpressionRequestTache1, ExpressionRequestTache2
from app.ia.prompts.prompt_orale_tache1 import prompt_orale_tache1
from app.ia.prompts.prompt_orale_tache2 import prompt_orale_tache2
from app.ia.prompts.prompt_orale_tache3 import prompt_orale_tache3
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

router = APIRouter(prefix="/expression-orale", tags=["expression-orale"])


def _generate_audio(modele_reponse: str) -> str | None:
    """Génère l'audio ElevenLabs et upload sur Firebase. Retourne l'URL ou None."""
    if not modele_reponse or not os.getenv("ELEVENLABS_API_KEY"):
        return None
    try:
        from app.core.elevenlabs_tts import synthesize_with_elevenlabs
        return synthesize_with_elevenlabs(modele_reponse)
    except Exception as e:
        print(f"⚠️ ElevenLabs TTS error: {e}")
        return None


def _stream_orale(texte: str, consigne: str, prompt_fn, model: str = "gpt-4o"):
    """
    1. Appelle GPT pour la correction (non-streaming pour avoir le JSON complet)
    2. Génère l'audio ElevenLabs du modele_reponse
    3. Streame le JSON final char par char + __END__JSON__
    """
    def stream():
        try:
            prompt = prompt_fn(texte, consigne)
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "Tu es un examinateur du TCF Canada. Réponds en JSON strict."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )

            raw = response.choices[0].message.content.strip()

            # Nettoyer le JSON (enlever ```json ... ``` si présent)
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
                if raw.endswith("```"):
                    raw = raw[:-3].strip()

            result = json.loads(raw)

            # Générer l'audio ElevenLabs
            modele = result.get("modele_reponse", "")
            audio_url = _generate_audio(modele)
            result["audio_modele_url"] = audio_url

            # Streamer le JSON final char par char
            final_json = json.dumps(result, ensure_ascii=False)
            for char in final_json:
                yield char
                time.sleep(0.003)

            yield "__END__JSON__"

        except json.JSONDecodeError:
            fallback = json.dumps({
                "tache_identifiee": "Expression Orale",
                "niveau_estime": "Erreur",
                "points_forts": "",
                "points_faibles": "Le format de réponse n'a pas pu être traité.",
                "note_sur_20": 0,
                "recommandation": "Réessayez.",
                "hors_sujet": "non",
                "justification_hors_sujet": "",
                "modele_reponse": "",
                "audio_modele_url": None
            }, ensure_ascii=False)
            yield fallback
            yield "__END__JSON__"

        except Exception as e:
            fallback = json.dumps({
                "tache_identifiee": "Expression Orale",
                "niveau_estime": "Erreur API",
                "points_forts": "",
                "points_faibles": str(e),
                "note_sur_20": 0,
                "recommandation": "Problème technique.",
                "hors_sujet": "non",
                "justification_hors_sujet": "",
                "modele_reponse": "",
                "audio_modele_url": None
            }, ensure_ascii=False)
            yield fallback
            yield "__END__JSON__"

    return StreamingResponse(stream(), media_type="text/plain")


@router.post("/tache1")
def analyser_orale_tache1(data: ExpressionRequestTache1):
    return _stream_orale(data.texte, data.consigne, prompt_orale_tache1)


@router.post("/tache2")
def analyser_orale_tache2(data: ExpressionRequestTache2):
    return _stream_orale(data.texte, data.consigne, prompt_orale_tache2)


@router.post("/tache3")
def analyser_orale_tache3(data: ExpressionRequestTache2):
    return _stream_orale(data.texte, data.consigne, prompt_orale_tache3)
