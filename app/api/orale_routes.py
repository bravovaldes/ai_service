import json
import os
import time
import uuid
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.ia.claude_client import chat_reply, generate_json
from app.ia.prompts.prompt_orale_tache1 import prompt_orale_tache1
from app.ia.prompts.prompt_orale_tache2 import prompt_orale_tache2
from app.ia.prompts.prompt_orale_tache2_chat import prompt_tache2_chat
from app.ia.prompts.prompt_orale_tache3 import prompt_orale_tache3
from app.schemas.expression_schema import (
    ExpressionRequestTache1,
    ExpressionRequestTache2,
    Tache2ChatRequest,
    Tache2ChatResponse,
)

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


def _stream_orale(texte: str, consigne: str, prompt_fn, tache_label: str):
    """
    1. Appelle Claude (non-stream) pour obtenir le JSON complet de la correction
    2. Génère l'audio Google TTS du modele_reponse
    3. Stream le JSON final char par char + __END__JSON__
    """
    def stream():
        prompt = prompt_fn(texte, consigne)
        result = generate_json(prompt, tache_identifiee=tache_label)

        # S'assurer que tache_identifiee est present meme si Claude l'oublie
        result.setdefault("tache_identifiee", tache_label)

        # Générer l'audio TTS du modele_reponse
        modele = result.get("modele_reponse", "")
        print(f"🔊 [Audio] modele_reponse ({len(modele)} chars)")
        result["audio_modele_url"] = _generate_audio(modele)

        # Stream char par char pour l'effet "ecriture en direct"
        final_json = json.dumps(result, ensure_ascii=False)
        for char in final_json:
            yield char
            time.sleep(0.003)

        yield "__END__JSON__"

    return StreamingResponse(stream(), media_type="text/plain")


@router.post("/tache1")
def analyser_orale_tache1(data: ExpressionRequestTache1):
    return _stream_orale(
        data.texte, data.consigne, prompt_orale_tache1, "Expression Orale - Tâche 1"
    )


@router.post("/tache2")
def analyser_orale_tache2(data: ExpressionRequestTache2):
    return _stream_orale(
        data.texte, data.consigne, prompt_orale_tache2, "Expression Orale - Tâche 2"
    )


@router.post("/tache3")
def analyser_orale_tache3(data: ExpressionRequestTache2):
    return _stream_orale(
        data.texte, data.consigne, prompt_orale_tache3, "Expression Orale - Tâche 3"
    )


@router.post("/tache2-chat", response_model=Tache2ChatResponse)
def tache2_chat(data: Tache2ChatRequest):
    """
    Chat interactif pour T2 Interaction.
    Claude joue le rôle de l'examinateur et répond naturellement au candidat.
    """
    openai_messages = prompt_tache2_chat(
        scenario=data.scenario,
        role_examinateur=data.role_examinateur,
        consigne=data.consigne,
        historique=[m.model_dump() for m in data.historique],
        message_candidat=data.message_candidat,
    )

    # Extraire le system du premier message (Claude attend system en param separe).
    system = ""
    messages = []
    for m in openai_messages:
        if m["role"] == "system":
            system = m["content"]
        else:
            messages.append(m)

    reply = chat_reply(system=system, messages=messages, max_tokens=300, temperature=0.8)
    return Tache2ChatResponse(reponse_examinateur=reply)
