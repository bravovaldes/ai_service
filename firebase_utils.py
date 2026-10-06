import os
import json
import firebase_admin
from firebase_admin import credentials, storage, firestore
from pathlib import Path

def initialize_firebase():
    if not firebase_admin._apps:
        # Priorité : variable d'env FIREBASE_SERVICE_ACCOUNT (pour Render/production)
        # Fallback : fichier serviceAccountKey.json (pour dev local)
        service_account_json = os.getenv("FIREBASE_SERVICE_ACCOUNT")
        if service_account_json:
            cred = credentials.Certificate(json.loads(service_account_json))
        else:
            cred = credentials.Certificate("serviceAccountKey.json")
        firebase_admin.initialize_app(cred, {
            "storageBucket": "tcf-canada-a828f.firebasestorage.app"
        })

def upload_audio_to_firebase(local_audio_path: str, firebase_folder: str = "audios") -> str:
    initialize_firebase()
    bucket = storage.bucket()
    filename = Path(local_audio_path).name
    blob = bucket.blob(f"{firebase_folder}/{filename}")
    blob.upload_from_filename(local_audio_path)
    blob.make_public()
    return blob.public_url

def url_si_existe(chemin: str) -> str | None:
    """L'URL publique du fichier s'il est deja la, sinon None.

    Sert au cache des audios synthetises : la meme phrase, dite par la
    meme voix a la meme vitesse, n'a aucune raison d'etre refabriquee.
    """
    try:
        initialize_firebase()
        blob = storage.bucket().blob(chemin)
        if not blob.exists():
            return None
        return blob.public_url
    except Exception as e:
        # Un cache qui echoue ne doit jamais empecher la synthese : on
        # repart simplement sur le chemin normal.
        print(f"[cache audio] verification impossible : {e}")
        return None


def save_question_to_firestore(data: dict):
    initialize_firebase()
    db = firestore.client()
    db.collection("question_comp_orale").add(data)
