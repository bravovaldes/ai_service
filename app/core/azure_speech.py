import os
import uuid
from pathlib import Path
from dotenv import load_dotenv
import azure.cognitiveservices.speech as speechsdk

load_dotenv()

def build_ssml(intro: str, question: str, options: list[str], voice: str = "fr-FR-HenriNeural"):
    ssml = """<speak version="1.0" xml:lang="fr-FR">"""

    # 🧔 Monsieur lit intro et question
    ssml += """
    <voice name="fr-FR-HenriNeural">
        <prosody rate="0%" pitch="0%">
            {intro}
            <break time="1000ms"/>
            {question}
            <break time="1000ms"/>
        </prosody>
    </voice>
    """.format(intro=intro, question=question)

    # 👩 Madame lit les options, après que Monsieur ait dit "Option A", "Option B", etc.
    for i, content in enumerate(options):
        label = chr(65 + i)  # 65 = A
        ssml += f"""
        <voice name="fr-FR-HenriNeural">
            <prosody rate="0%" pitch="0%">
                Option {label}.
                <break time="400ms"/>
            </prosody>
        </voice>
        <voice name="fr-FR-DeniseNeural">
            <prosody rate="0%" pitch="0%">
                {content}
                <break time="800ms"/>
            </prosody>
        </voice>
        """

    ssml += "</speak>"
    return ssml


def synthesize_speech(intro: str, question: str, options: list[str], voice: str = "fr-FR-HenriNeural", format: str = "audio-16khz-128kbitrate-mono-mp3") -> str:
    from dotenv import load_dotenv
    load_dotenv()

    speech_key = os.getenv("AZURE_API_KEY")
    speech_region = os.getenv("AZURE_REGION")

    if not speech_key or not speech_region:
        raise ValueError("AZURE_API_KEY or AZURE_REGION is missing")

    speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=speech_region)
    speech_config.speech_synthesis_voice_name = voice
    speech_config.set_speech_synthesis_output_format(
        speechsdk.SpeechSynthesisOutputFormat.Audio16Khz128KBitRateMonoMp3
    )

    # 🟡 Génère le chemin du fichier
    file_id = f"{uuid.uuid4()}.mp3"
    output_path = Path("static/audio") / file_id
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 🔧 Crée la config avec ce chemin
    audio_config = speechsdk.audio.AudioOutputConfig(filename=str(output_path))

    # 🔊 Génère le SSML
    ssml = build_ssml(intro, question, options, voice)
    synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
    result = synthesizer.speak_ssml_async(ssml).get()

    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        return str(output_path)  # ✅ On retourne simplement le chemin que nous avons généré
    else:
        raise Exception(f"Erreur de synthèse : {result.reason}")
