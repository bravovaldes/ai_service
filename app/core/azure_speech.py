import os
import uuid
from pathlib import Path
from dotenv import load_dotenv
import azure.cognitiveservices.speech as speechsdk
import json
from firebase_admin import firestore
from tqdm import tqdm
from firebase_utils import initialize_firebase, upload_audio_to_firebase

load_dotenv()

def build_ssml(intro: str, contexte: str, question: str, options: list[str], voice_intro="fr-FR-HenriNeural") -> str:
    ssml = """<speak version="1.0" xml:lang="fr-FR">"""

    # 🧔 Henri lit : intro, contexte, question
    ssml += f"""
    <voice name="{voice_intro}">
        <prosody rate="-10%" pitch="0%">
            {intro}
            <break time="1200ms"/>
            {contexte}
            <break time="1000ms"/>
            {question}
            <break time="1000ms"/>
        </prosody>
    </voice>
    """

    # 👨 Henri et 👩 Denise lisent les options
    for i, content in enumerate(options):
        label = chr(65 + i)
        ssml += f"""
        <voice name="{voice_intro}">
            <prosody rate="-10%" pitch="0%">
                Option {label}.
                <break time="400ms"/>
            </prosody>
        </voice>
        <voice name="fr-FR-DeniseNeural">
            <prosody rate="-10%" pitch="0%">
                {content}
                <break time="800ms"/>
            </prosody>
        </voice>
        """

    ssml += "</speak>"
    return ssml


def synthesize_speech(intro: str, contexte: str, question: str, options: list[str]) -> str:
    speech_key = os.getenv("AZURE_API_KEY")
    speech_region = os.getenv("AZURE_REGION")

    if not speech_key or not speech_region:
        raise ValueError("AZURE_API_KEY or AZURE_REGION is missing")

    speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=speech_region)
    speech_config.set_speech_synthesis_output_format(
        speechsdk.SpeechSynthesisOutputFormat.Audio16Khz128KBitRateMonoMp3
    )

    file_id = f"{uuid.uuid4()}.mp3"
    output_path = Path("static/audio") / file_id
    output_path.parent.mkdir(parents=True, exist_ok=True)

    audio_config = speechsdk.audio.AudioOutputConfig(filename=str(output_path))

    ssml = build_ssml(intro, contexte, question, options)
    synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
    result = synthesizer.speak_ssml_async(ssml).get()

    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        return str(output_path)
    else:
        raise Exception(f"Erreur de synthèse : {result.reason}")


def enrich_and_upload_questions(json_path="tools/questions_a1_a2_completes.json", firebase_folder="audios"):
    initialize_firebase()
    db = firestore.client()

    with open(json_path, "r", encoding="utf-8") as f:
        questions = json.load(f)

    intro_text = "Écoutez attentivement la question et les 4 propositions suivantes."

    for q in tqdm(questions, desc="Traitement des questions"):
        try:
            contexte = q.get("contexte", "")
            audio_local_path = synthesize_speech(
                intro=intro_text,
                contexte=contexte,
                question=q["question"],
                options=q["propositions"]
            )

            audio_url = upload_audio_to_firebase(audio_local_path, firebase_folder)

            texte_audio = f"{intro_text} {contexte} {q['question']} {', '.join(q['propositions'])}"

            enriched_question = {
                **q,
                "audioUrl": audio_url,
                "texte_audio": texte_audio
            }

            doc_ref = db.collection("question_comp_orale").document()
            doc_ref.set(enriched_question)

        except Exception as e:
            print(f"❌ Erreur sur la question : {q.get('question', '[inconnue]')}\n{e}")


if __name__ == "__main__":
    enrich_and_upload_questions(
        json_path="tools/questions_a1_a2_completes.json",
        firebase_folder="audios"
    )
