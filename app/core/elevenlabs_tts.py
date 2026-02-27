import os
import uuid
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
# Voix française masculine naturelle — "Thomas" (FR)
DEFAULT_VOICE_ID = "GBv7mTt0atIp3Br8iCZE"  # Thomas - voix française masculine


def get_french_voice_id() -> str:
    """Récupère une voix française disponible, ou utilise la voix par défaut."""
    if not ELEVENLABS_API_KEY:
        raise ValueError("ELEVENLABS_API_KEY manquante dans .env")

    try:
        resp = requests.get(
            "https://api.elevenlabs.io/v1/voices",
            headers={"xi-api-key": ELEVENLABS_API_KEY},
            timeout=10,
        )
        if resp.status_code == 200:
            voices = resp.json().get("voices", [])
            # Chercher une voix avec label français
            for v in voices:
                labels = v.get("labels", {})
                lang = labels.get("language", "").lower()
                if "french" in lang or "français" in lang:
                    return v["voice_id"]
    except Exception:
        pass

    return DEFAULT_VOICE_ID


def synthesize_with_elevenlabs(text: str, voice_id: str = None) -> str:
    """
    Convertit du texte en audio via ElevenLabs TTS.
    Retourne l'URL publique Firebase du fichier audio.
    """
    if not ELEVENLABS_API_KEY:
        raise ValueError("ELEVENLABS_API_KEY manquante dans .env")

    if voice_id is None:
        voice_id = get_french_voice_id()

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
    }

    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75,
            "style": 0.3,
            "use_speaker_boost": True,
        },
    }

    resp = requests.post(url, json=payload, headers=headers, timeout=60)

    if resp.status_code != 200:
        raise Exception(f"ElevenLabs TTS error {resp.status_code}: {resp.text[:200]}")

    # Sauvegarder en local temporairement
    file_id = f"orale_modele_{uuid.uuid4()}.mp3"
    output_path = Path("static/audio") / file_id
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "wb") as f:
        f.write(resp.content)

    # Upload vers Firebase Storage (import lazy pour éviter crash si firebase-admin absent)
    from firebase_utils import upload_audio_to_firebase
    firebase_url = upload_audio_to_firebase(str(output_path), "audios_orale")

    # Nettoyage local
    try:
        os.remove(str(output_path))
    except Exception:
        pass

    return firebase_url
