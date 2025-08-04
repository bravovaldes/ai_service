import os
import uuid
from pathlib import Path
from dotenv import load_dotenv
import azure.cognitiveservices.speech as speechsdk

load_dotenv()

OUTPUT_DIR = Path("static/audio")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

speech_key = os.getenv("AZURE_API_KEY")
speech_region = os.getenv("AZURE_REGION")

def synthesize_question_format(question_text: str, options: list[str]) -> str:
    """
    Génère un fichier MP3 avec Azure Speech :
    - Question en voix masculine
    - Options en voix féminine
    - Pauses naturelles
    """
    speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=speech_region)
    speech_config.speech_synthesis_output_format = (
        speechsdk.SpeechSynthesisOutputFormat.Audio16Khz32KBitRateMonoMp3
    )

    output_path = OUTPUT_DIR / f"{uuid.uuid4()}_question.mp3"
    audio_config = speechsdk.audio.AudioOutputConfig(filename=str(output_path))

    synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)

    # ⚡ SSML pour voix et pauses
    ssml = f"""
    <speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xml:lang='fr-FR'>
        <voice name='fr-FR-HenriNeural'>
            {question_text}
            <break time='1200ms'/>
        </voice>
    """

    for i, opt in enumerate(options):
        label = chr(65 + i)
        ssml += f"""
        <voice name='fr-FR-DeniseNeural'>
            Option {label}. {opt}
            <break time='800ms'/>
        </voice>
        """

    ssml += "</speak>"

    result = synthesizer.speak_ssml_async(ssml).get()

    if result.reason != speechsdk.ResultReason.SynthesizingAudioCompleted:
        raise Exception(f"Erreur Azure Speech: {result.reason}")

    return str(output_path)
