import io
import json
import os
import re
import wave
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
    Tache2TourResponse,
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


def _generate_audio(modele_reponse: str, vitesse: float = 1.0) -> str | None:
    """Génère l'audio via Google Cloud TTS (Neural2-C, fr-FR) et upload sur Firebase.

    `vitesse` sert au dialogue de la tâche 2. La voix par défaut débite au
    rythme d'un natif pressé : un candidat B1 n'a pas le temps de traiter la
    phrase, et l'exercice devient un test de compréhension rapide au lieu
    d'un exercice d'interaction. Un examinateur réel, lui, s'adapte à la
    personne en face de lui.
    """
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
            speaking_rate=vitesse,
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


def _contexte_prosodique(mesures: dict | None, prononciation: str = "") -> str:
    """Le bloc de texte qui porte les mesures audio jusqu'au correcteur.

    Extrait de /tache{numero}/audio pour servir aussi a la tache 2, dont les
    mesures arrivent par un autre chemin — agregees par le client plutot que
    tirees d'un fichier unique.
    """
    if not mesures:
        return ""
    lignes = [
        f"- debit : {mesures.get('debit_mots_minute')} mots par minute",
        f"- silence : {round(mesures.get('taux_silence') or 0)} % du temps, "
        f"{mesures.get('nb_pauses')} pause(s) marquee(s)",
        f"- hesitations : {mesures.get('nb_hesitations')} "
        f"({round(mesures.get('taux_hesitation') or 0)} %)",
        f"- repetitions : {mesures.get('repetitions')}",
        f"- duree de parole : {round(mesures.get('duree_secondes') or 0)} s "
        f"pour {mesures.get('nb_mots')} mots",
    ]
    return (
        "\n\n---\n"
        "MESURES ISSUES DE L'ENREGISTREMENT AUDIO\n"
        "Ces chiffres proviennent de l'audio lui-meme, pas du texte. "
        "Utilise-les pour juger la FLUIDITE et l'AISANCE, criteres que la "
        "transcription seule ne permet pas d'evaluer.\n\n"
        + "\n".join(lignes)
        + (f"\n{prononciation}" if prononciation else "")
        + "\n\nTiens-en compte dans « points_forts », « points_faibles » et la "
        "note : un discours fluide et continu vaut mieux qu'un discours hache "
        "de silences, a contenu egal.\n"
    )


@router.post("/tache1")
def analyser_orale_tache1(data: ExpressionRequestTache1):
    return _stream_orale(
        data.texte, data.consigne, prompt_orale_tache1, "Expression Orale - Tâche 1"
    )


@router.post("/tache2")
def analyser_orale_tache2(data: ExpressionRequestTache2):
    # La tache 2 est un dialogue : il n'existe pas de fichier unique a
    # transcrire. Le client agrege les mesures rendues tour par tour et les
    # joint ici, pour que la correction d'une epreuve orale puisse parler de
    # fluidite comme elle le fait pour les taches 1 et 3.
    return _stream_orale(
        data.texte,
        data.consigne,
        prompt_orale_tache2,
        "Expression Orale - Tâche 2",
        contexte_oral=_contexte_prosodique(data.analyse_audio),
        mesures=data.analyse_audio,
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


# Deux voix francaises nettement distinctes. Un dialogue lu par une seule
# voix n'est pas un dialogue : on ne sait pas qui parle, et l'oreille doit
# faire le travail que la scene devrait faire pour elle.
_VOIX_CANDIDAT = "fr-FR-Neural2-B"      # homme
_VOIX_INTERLOCUTEUR = "fr-FR-Neural2-C"  # femme

_MARQUEUR = re.compile(r"^\s*[\[(]\s*(interlocuteur|examinateur|candidat|vous|moi)\s*[\])]\s*:?\s*", re.I)


def _decouper_dialogue(texte: str) -> list[tuple[str, str]]:
    """Separe un modele de reponse en repliques (voix, texte).

    Le modele de la tache 2 est un DIALOGUE : il alterne les repliques du
    candidat et celles de son interlocuteur, ces dernieres precedees de
    « [Interlocuteur] ». Lu par une seule voix, le marqueur etait prononce
    a voix haute — « crochet interlocuteur » — et les deux roles se
    confondaient.

    On retire donc le marqueur et on s'en sert pour choisir la voix.
    """
    repliques: list[tuple[str, str]] = []
    for bloc in re.split(r"\n\s*\n|\n", texte):
        bloc = bloc.strip()
        if not bloc:
            continue
        m = _MARQUEUR.match(bloc)
        if m:
            role = m.group(1).lower()
            voix = (
                _VOIX_CANDIDAT
                if role in ("candidat", "vous", "moi")
                else _VOIX_INTERLOCUTEUR
            )
            bloc = _MARQUEUR.sub("", bloc).strip()
        else:
            # Sans marqueur, c'est le candidat qui parle : le modele est
            # ecrit de son point de vue.
            voix = _VOIX_CANDIDAT
        if bloc:
            repliques.append((voix, bloc))
    return repliques


def _synthese_dialogue(texte: str, vitesse: float = 0.92) -> str | None:
    """Synthetise un dialogue a deux voix, avec des silences entre repliques.

    Chaque replique est synthetisee separement puis les PCM sont mis bout a
    bout, avec 420 ms de silence entre chaque. Ce blanc n'est pas un detail :
    sans lui, les repliques se chevauchent a l'oreille et le dialogue devient
    un bloc de parole qu'on n'arrive pas a suivre — exactement ce qu'on
    reprochait a la version lue d'une seule traite.
    """
    repliques = _decouper_dialogue(texte)
    if not repliques:
        return None
    if len(repliques) == 1:
        return _generate_audio(repliques[0][1], vitesse=vitesse)

    try:
        from google.cloud import texttospeech

        tts = _get_tts_client()
        taux = 24000
        morceaux: list[bytes] = []
        silence = b"\x00\x00" * int(taux * 0.42)

        for i, (voix, replique) in enumerate(repliques):
            reponse = tts.synthesize_speech(
                input=texttospeech.SynthesisInput(text=replique),
                voice=texttospeech.VoiceSelectionParams(
                    language_code="fr-FR", name=voix
                ),
                audio_config=texttospeech.AudioConfig(
                    audio_encoding=texttospeech.AudioEncoding.LINEAR16,
                    sample_rate_hertz=taux,
                    speaking_rate=vitesse,
                ),
            )
            with wave.open(io.BytesIO(reponse.audio_content), "rb") as w:
                morceaux.append(w.readframes(w.getnframes()))
            if i < len(repliques) - 1:
                morceaux.append(silence)

        tampon = io.BytesIO()
        with wave.open(tampon, "wb") as sortie:
            sortie.setnchannels(1)
            sortie.setsampwidth(2)
            sortie.setframerate(taux)
            sortie.writeframes(b"".join(morceaux))

        file_id = f"orale_dialogue_{uuid.uuid4()}.wav"
        chemin = Path("static/audio") / file_id
        chemin.parent.mkdir(parents=True, exist_ok=True)
        chemin.write_bytes(tampon.getvalue())

        from firebase_utils import upload_audio_to_firebase

        url = upload_audio_to_firebase(str(chemin), "audios_orale")
        try:
            os.remove(str(chemin))
        except Exception:
            pass
        return url
    except Exception as e:
        print(f"[Dialogue] echec : {e}")
        # Mieux vaut une voix unique que pas de son du tout.
        return _generate_audio(texte, vitesse=vitesse)


@router.post("/synthese-dialogue")
def synthese_dialogue(texte: str = Form(...)):
    """Lit un modele de reponse de la tache 2 comme une vraie conversation.

    Une voix par role, un blanc entre les repliques, et un debit pose. Le
    but du modele est de faire entendre le RYTHME d'un echange reussi : lu
    d'une traite par une seule voix, il ne le fait pas.
    """
    return {"audio_url": _synthese_dialogue(texte)}


@router.post("/tache2/tour", response_model=Tache2TourResponse)
def tache2_tour(
    scenario: str = Form(...),
    role_examinateur: str = Form(...),
    consigne: str = Form(...),
    historique: str = Form("[]"),
    fichier: UploadFile = File(...),
):
    """Un tour de dialogue de la tache 2, de bout en bout.

    La tache 2 est une INTERACTION : le candidat pose des questions, un
    interlocuteur repond. L'application faisait jusqu'ici transcrire le
    telephone par `speech_to_text`, puis affichait la reponse de
    l'examinateur en TEXTE. Deux problemes, et le second est le plus grave.

    · La transcription de l'appareil est approximative et ne rend ni temps ni
      hesitations : la correction d'une epreuve orale ne pouvait rien dire de
      l'aisance. Et sur Android le micro est exclusif, donc impossible
      d'enregistrer en meme temps qu'on ecoute l'appareil transcrire.

    · **Lire les repliques de l'examinateur n'entraine a rien.** Le jour de
      l'epreuve, il faut comprendre a l'oreille, a la vitesse de l'autre,
      sans pouvoir relire. Un dialogue ecrit est un exercice de lecture
      deguise en exercice oral.

    Tout se fait donc ici, en un aller-retour — ce qui compte sur une
    connexion lente : transcription Scribe avec les temps mot a mot, reponse
    de l'examinateur, et synthese vocale de cette reponse. Les mesures du
    tour repartent avec, le client les agrege pour la correction finale.
    """
    contenu = fichier.file.read()
    t = transcrire(contenu, fichier.filename or "tour.m4a")

    if t is None or not t.texte.strip():
        # Sans transcription il n'y a pas de tour : repondre quand meme
        # ferait dialoguer l'examinateur avec le silence.
        return Tache2TourResponse(
            transcription="",
            reponse_examinateur="",
            erreur=(
                "Je ne t'ai pas entendu. Verifie ton micro et reessaie — "
                "ton tour n'est pas perdu."
            ),
        )

    try:
        passe = json.loads(historique) if historique else []
    except json.JSONDecodeError:
        passe = []

    messages_openai = prompt_tache2_chat(
        scenario=scenario,
        role_examinateur=role_examinateur,
        consigne=consigne,
        historique=passe,
        message_candidat=t.texte,
    )
    system = ""
    messages = []
    for m in messages_openai:
        if m["role"] == "system":
            system = m["content"]
        else:
            messages.append(m)

    reponse = chat_reply(
        system=system, messages=messages, max_tokens=300, temperature=0.8
    )

    return Tache2TourResponse(
        transcription=t.texte,
        reponse_examinateur=reponse,
        # Un peu en dessous du débit natif : assez lent pour être suivi,
        # assez vif pour rester une vraie conversation.
        audio_url=_generate_audio(reponse, vitesse=0.9),
        analyse_audio=t.pour_le_client(),
    )


@router.post("/synthese")
def synthese(texte: str = Form(...)):
    """Synthetise un texte quelconque, a la demande.

    Sert d'abord a lire la CORRECTION a voix haute. Sur une epreuve orale,
    ecouter son retour plutot que le lire a du sens : on entend le ton, on
    peut fermer les yeux, et surtout on peut l'ecouter en marchant.

    Meme implementation que /audio-modele, qui reste pour compatibilite.
    """
    return {"audio_url": _generate_audio(texte)}


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
