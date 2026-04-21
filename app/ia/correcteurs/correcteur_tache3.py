from fastapi.responses import StreamingResponse

from app.ia.claude_client import stream_correction
from app.ia.prompts.prompt_tache3 import prompt_tache3


def corriger_tache3(texte: str, document1: str, document2: str, consigne: str):
    prompt = prompt_tache3(texte, document1, document2, consigne)
    return StreamingResponse(stream_correction(prompt), media_type="text/plain")
