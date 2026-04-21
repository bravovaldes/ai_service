from fastapi.responses import StreamingResponse

from app.ia.claude_client import stream_correction
from app.ia.prompts.prompt_tache1 import prompt_tache1


def corriger_tache1(texte: str, consigne: str):
    prompt = prompt_tache1(texte, consigne)
    return StreamingResponse(stream_correction(prompt), media_type="text/plain")
