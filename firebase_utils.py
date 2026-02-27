import firebase_admin
from firebase_admin import credentials, storage, firestore
from pathlib import Path

def initialize_firebase():
    if not firebase_admin._apps:
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

def save_question_to_firestore(data: dict):
    initialize_firebase()
    db = firestore.client()
    db.collection("question_comp_orale").add(data)
