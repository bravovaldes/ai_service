import json

from anthropic import Anthropic
from dotenv import load_dotenv
from fastapi.responses import StreamingResponse
import os

from app.ia.prompts.prompt_tache1 import prompt_tache1

load_dotenv()
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# Opus 4.7 refuse certains inputs bizarres (stop_reason=refusal) avec 0 output.
# Opus 4.6 est tres proche en qualite et gere correctement le cas hors_sujet.
MODEL = "claude-opus-4-6"


def _refusal_payload() -> str:
    """JSON synthetique renvoye si le modele refuse (ou sort vide) —
    le frontend attend toujours un blob parseable."""
    return json.dumps(
        {
            "niveau_estime": "A1",
            "points_forts": "",
            "points_faibles": (
                "Le texte soumis ne constitue pas une production "
                "exploitable : il est illisible, incoherent ou absent."
            ),
            "note_sur_20": 0,
            "recommandation": (
                "Veuillez soumettre un texte redige en francais qui "
                "repond a la consigne."
            ),
            "hors_sujet": "oui",
            "justification_hors_sujet": (
                "Texte incoherent ou non exploitable (detection automatique)."
            ),
            "modele_reponse": "",
        },
        ensure_ascii=False,
    )


def corriger_tache1(texte: str, consigne: str):
    prompt = prompt_tache1(texte, consigne)

    def stream():
        emitted_any = False
        emitted_sentinel = False
        stop_reason = None

        with client.messages.stream(
            model=MODEL,
            max_tokens=8192,
            temperature=0.7,
            messages=[{"role": "user", "content": prompt}],
        ) as response:
            for text in response.text_stream:
                if not text:
                    continue
                emitted_any = True
                yield text
                if "__END__JSON__" in text:
                    emitted_sentinel = True
            try:
                final = response.get_final_message()
                stop_reason = final.stop_reason
            except Exception:
                pass

        # Refus / output vide → renvoyer un JSON hors_sujet synthetique
        if not emitted_any or stop_reason == "refusal":
            yield _refusal_payload()
            yield "\n__END__JSON__"
            return

        # Garde-fou : si Claude a oublie la sentinelle, on l'ajoute
        if not emitted_sentinel:
            yield "\n__END__JSON__"

    return StreamingResponse(stream(), media_type="text/plain")
