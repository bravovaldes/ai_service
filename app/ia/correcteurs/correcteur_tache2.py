from fastapi.responses import StreamingResponse

from app.ia.claude_client import stream_correction
from app.ia.prompts.prompt_tache2 import prompt_tache2


def corriger_tache2(texte: str, consigne: str):
    prompt = prompt_tache2(texte, consigne)
    return StreamingResponse(stream_correction(prompt), media_type="text/plain")
