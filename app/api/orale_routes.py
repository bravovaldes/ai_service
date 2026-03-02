import os
import json
import time
import uuid
from pathlib import Path
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from app.schemas.expression_schema import (
    ExpressionRequestTache1,
    ExpressionRequestTache2,
    Tache2ChatRequest,
    Tache2ChatResponse,
)
from app.ia.prompts.prompt_orale_tache2_chat import prompt_tache2_chat
from app.ia.prompts.prompt_orale_tache1 import prompt_orale_tache1
from app.ia.prompts.prompt_orale_tache2 import prompt_orale_tache2
from app.ia.prompts.prompt_orale_tache3 import prompt_orale_tache3
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

router = APIRouter(prefix="/expression-orale", tags=["expression-orale"])


def _get_tts_client():
    """Retourne un client Google Cloud TTS authentifié.

    Sur Render.com : ajouter GOOGLE_CREDENTIALS_JSON dans les env vars
    (coller le contenu entier du fichier JSON de compte de service).
    En local : utiliser GOOGLE_APPLICATION_CREDENTIALS ou GOOGLE_CREDENTIALS_JSON.
    """
    creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
    if creds_json:
        from google.oauth2 import service_account
        from google.cloud import texttospeech
        creds_dict = json.loads(creds_json)
        credentials = service_account.Credentials.from_service_account_info(
            creds_dict,
            scopes=["https://www.googleapis.com/auth/cloud-platform"],
        )
        return texttospeech.TextToSpeechClient(credentials=credentials)
    from google.cloud import texttospeech
    return texttospeech.TextToSpeechClient()  # ADC (GOOGLE_APPLICATION_CREDENTIALS)


def _generate_audio(modele_reponse: str) -> str | None:
    """Génère l'audio via Google Cloud TTS (Neural2-C, fr-FR) et upload sur Firebase."""
    if not modele_reponse:
        print("🔊 [Audio] modele_reponse vide → pas d'audio")
        return None
    try:
        from google.cloud import texttospeech
        print(f"🔊 [Audio] Appel Google Cloud TTS ({len(modele_reponse)} chars)...")
        tts = _get_tts_client()
        synthesis_input = texttospeech.SynthesisInput(text=modele_reponse)
        voice = texttospeech.VoiceSelectionParams(
            language_code="fr-FR",
            name="fr-FR-Neural2-C",  # Voix française naturelle (femme)
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.LINEAR16,  # WAV — compatible ExoPlayer
        )
        response = tts.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config,
        )
        file_id = f"orale_modele_{uuid.uuid4()}.wav"
        output_path = Path("static/audio") / file_id
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(str(output_path), "wb") as f:
            f.write(response.audio_content)
        print(f"🔊 [Audio] Google TTS OK, upload Firebase...")
        from firebase_utils import upload_audio_to_firebase
        url = upload_audio_to_firebase(str(output_path), "audios_orale")
        try:
            os.remove(str(output_path))
        except Exception:
            pass
        print(f"🔊 [Audio] Audio prêt → url={url}")
        return url
    except Exception as e:
        print(f"❌ [Audio] Google TTS error: {e}")
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

            # Générer l'audio Google Cloud TTS
            modele = result.get("modele_reponse", "")
            print(f"🔊 [Audio] modele_reponse dans le résultat GPT: '{modele[:80] if modele else 'VIDE'}...'")
            audio_url = _generate_audio(modele)
            result["audio_modele_url"] = audio_url
            print(f"🔊 [Audio] audio_modele_url final = {audio_url}")

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


@router.post("/tache2-chat", response_model=Tache2ChatResponse)
def tache2_chat(data: Tache2ChatRequest):
    """
    Chat interactif pour T2 Interaction.
    Le candidat envoie son message + l'historique complet.
    GPT-4o joue le rôle de l'examinateur et répond.
    """
    try:
        messages = prompt_tache2_chat(
            scenario=data.scenario,
            role_examinateur=data.role_examinateur,
            consigne=data.consigne,
            historique=[m.model_dump() for m in data.historique],
            message_candidat=data.message_candidat,
        )

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.8,
            max_tokens=200,
        )

        reply = response.choices[0].message.content.strip()
        return Tache2ChatResponse(reponse_examinateur=reply)

    except Exception as e:
        print(f"⚠️ Tache2 chat error: {e}")
        return Tache2ChatResponse(
            reponse_examinateur="Excusez-moi, pouvez-vous répéter s'il vous plaît ?"
        )
