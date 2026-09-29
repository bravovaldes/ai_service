import json
import os
import time
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import StreamingResponse

from app.ia.claude_client import chat_reply, generate_json
from app.core.transcription import transcrire
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


def _stream_orale(
    texte: str,
    consigne: str,
    prompt_fn,
    tache_label: str,
    contexte_oral: str = "",
    mesures: dict | None = None,
):
    """Renvoie la correction des qu'elle est prete.

    Trois gaspillages ont ete retires ici, mesures sur une correction reelle
    de 33,7 s dont 24 s d'ecran fige avant le moindre octet :

    · L'animation factice. Le JSON etait reemis caractere par caractere avec
      `time.sleep(0.003)` pour imiter une ecriture en direct. Sur 3 146
      caracteres, cela ajoutait **9,4 secondes d'attente pure** apres que la
      reponse etait deja connue. L'effet est desormais l'affaire du client,
      qui peut animer sans faire patienter le reseau.

    · La synthese vocale sur le chemin critique. L'audio du modele de reponse
      etait genere AVANT l'envoi, alors que l'utilisateur lit d'abord sa
      correction et n'ecoute le modele qu'apres, souvent jamais. Il est
      desormais produit a la demande par /audio-modele.

    · L'envoi en un bloc. On emet maintenant des que le JSON est pret.
    """
    def stream():
        prompt = prompt_fn(texte, consigne)
        # Le contexte prosodique s'ajoute au prompt existant plutot que de le
        # remplacer : les consignes de notation restent celles qui ont ete
        # reglees a l'usage, on ne fait qu'ajouter ce que le texte seul ne
        # disait pas.
        if contexte_oral:
            prompt += contexte_oral
        result = generate_json(prompt, tache_identifiee=tache_label)

        # S'assurer que tache_identifiee est present meme si Claude l'oublie
        result.setdefault("tache_identifiee", tache_label)

        # L'audio du modele n'est plus genere ici : il coutait environ 4 s
        # sur le chemin critique pour un contenu que l'utilisateur n'ecoute
        # qu'apres avoir lu sa correction, quand il l'ecoute. Le client le
        # demande a /audio-modele au moment du clic.
        result["audio_modele_url"] = None
        if mesures:
            result["analyse_audio"] = mesures

        yield json.dumps(result, ensure_ascii=False)
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


_PROMPTS = {
    1: (prompt_orale_tache1, "Expression Orale - Tâche 1"),
    2: (prompt_orale_tache2, "Expression Orale - Tâche 2"),
    3: (prompt_orale_tache3, "Expression Orale - Tâche 3"),
}


@router.post("/tache{numero}/audio")
def analyser_orale_audio(
    numero: int,
    consigne: str = Form(...),
    fichier: UploadFile = File(...),
):
    """Correction a partir de l'AUDIO plutot que d'une transcription telephone.

    L'application transcrivait jusqu'ici sur l'appareil avec `speech_to_text`,
    qui ne rend qu'une suite de mots : ni temps, ni hesitations, ni confiance.
    Claude jugeait donc une production orale sans rien percevoir du debit, des
    pauses ou de l'aisance — c'est-a-dire l'essentiel de ce que l'examinateur
    evalue, et ce qui separe un B2 d'un C1.

    Ici l'audio est transcrit par Scribe, qui rend les temps mot a mot. On en
    tire debit, pauses et hesitations, et on les joint au prompt.

    L'ancien point d'entree reste actif : une application non mise a jour
    continue de fonctionner.
    """
    prompt_fn, label = _PROMPTS.get(numero, _PROMPTS[1])
    contenu = fichier.file.read()
    t = transcrire(contenu, fichier.filename or "audio.m4a")

    if t is None or not t.texte.strip():
        # On ne fabrique pas une note a partir de rien : mieux vaut le dire.
        def echec():
            yield json.dumps(
                {
                    "tache_identifiee": label,
                    "niveau_estime": "",
                    "points_forts": "",
                    "points_faibles": "",
                    "note_sur_20": None,
                    "recommandation": (
                        "L'enregistrement n'a pas pu etre transcrit. Verifie que "
                        "tu as bien parle et que le micro fonctionne, puis "
                        "recommence."
                    ),
                    "erreur_technique": "oui",
                },
                ensure_ascii=False,
            )
            yield "__END__JSON__"

        return StreamingResponse(echec(), media_type="text/plain")

    contexte = (
        "\n\n---\n"
        "MESURES ISSUES DE L'ENREGISTREMENT AUDIO\n"
        "Ces chiffres proviennent de l'audio lui-meme, pas du texte. "
        "Utilise-les pour juger la FLUIDITE et l'AISANCE, criteres que la "
        "transcription seule ne permet pas d'evaluer.\n\n"
        f"{t.prosodie.resume()}\n"
        f"{t.indice_prononciation()}\n\n"
        "Tiens-en compte dans « points_forts », « points_faibles » et la note : "
        "un discours fluide et continu vaut mieux qu'un discours hache de "
        "silences, a contenu egal.\n"
    )

    # Les mesures accompagnent la correction : l'utilisateur doit pouvoir
    # verifier ce que le correcteur a entendu et sur quoi il se fonde.
    return _stream_orale(
        t.texte,
        consigne,
        prompt_fn,
        label,
        contexte_oral=contexte,
        mesures=t.pour_le_client(),
    )


@router.post("/audio-modele")
def audio_modele(texte: str = Form(...)):
    """Synthetise le modele de reponse, a la demande.

    Separe de la correction pour ne pas faire attendre l'utilisateur pour un
    fichier qu'il n'ecoutera peut-etre jamais.
    """
    url = _generate_audio(texte)
    return {"audio_modele_url": url}


@router.post("/tache2-chat", response_model=Tache2ChatResponse)
def tache2_chat(data: Tache2ChatRequest):
    """
    Chat interactif pour T2 Interaction.
    Claude joue le rôle de l'examinateur et répond naturellement au candidat.
    """
    messages_bruts = prompt_tache2_chat(
        scenario=data.scenario,
        role_examinateur=data.role_examinateur,
        consigne=data.consigne,
        historique=[m.model_dump() for m in data.historique],
        message_candidat=data.message_candidat,
    )

    # Extraire le system du premier message (Claude attend system en param separe).
    system = ""
    messages = []
    for m in messages_bruts:
        if m["role"] == "system":
            system = m["content"]
        else:
            messages.append(m)

    reply = chat_reply(system=system, messages=messages, max_tokens=300, temperature=0.8)
    return Tache2ChatResponse(reponse_examinateur=reply)
