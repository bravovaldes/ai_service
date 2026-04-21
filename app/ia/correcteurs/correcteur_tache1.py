from fastapi.responses import StreamingResponse
from anthropic import Anthropic
import os
from dotenv import load_dotenv
from app.ia.prompts.prompt_tache1 import prompt_tache1

load_dotenv()
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

MODEL = "claude-opus-4-7"


def corriger_tache1(texte: str, consigne: str):
    prompt = prompt_tache1(texte, consigne)

    def stream():
        emitted_sentinel = False
        with client.messages.stream(
            model=MODEL,
            max_tokens=8192,
            messages=[{"role": "user", "content": prompt}],
        ) as response:
            for text in response.text_stream:
                if not text:
                    continue
                yield text
                if "__END__JSON__" in text:
                    emitted_sentinel = True
        # Garde-fou : si Claude n'a pas emis la sentinelle (truncation / oubli),
        # on la rajoute pour que le parsing frontend reussisse toujours.
        if not emitted_sentinel:
            yield "\n__END__JSON__"

    return StreamingResponse(stream(), media_type="text/plain")
