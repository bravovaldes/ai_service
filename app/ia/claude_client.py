"""Helper centralise pour les appels Claude (Anthropic).

Regroupe :
- La creation du client
- Le streaming des corrections ecrites (yield text/plain + sentinelle __END__JSON__)
- L'appel non-stream pour l'expression orale (recuperer un JSON complet avant
  injection d'audio)
- La gestion uniforme des refus (stop_reason=refusal) : payload hors_sujet
  synthetique au lieu d'une sortie vide qui ferait planter le frontend.
"""
import json
import os
from typing import Iterable, Optional

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

# Opus 4.6 = meilleur qualite disponible sans les refus stricts d'Opus 4.7
# (qui renvoie stop_reason=refusal + 0 token sur gibberish / transcriptions
# partielles, ce qui casse le parsing frontend).
MODEL = "claude-opus-4-6"

_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


def get_client() -> Anthropic:
    return _client


def _refusal_payload(tache_identifiee: str = "") -> dict:
    payload = {
        "niveau_estime": "A1",
        "points_forts": "",
        "points_faibles": (
            "Le texte soumis ne constitue pas une production exploitable : "
            "il est illisible, incoherent ou absent."
        ),
        "note_sur_20": 0,
        "recommandation": (
            "Veuillez soumettre un texte (ou un enregistrement) qui repond "
            "a la consigne."
        ),
        "hors_sujet": "oui",
        "justification_hors_sujet": (
            "Production incoherente ou non exploitable (detection automatique)."
        ),
        "modele_reponse": "",
    }
    if tache_identifiee:
        payload["tache_identifiee"] = tache_identifiee
    return payload


def stream_correction(
    prompt: str,
    *,
    max_tokens: int = 8192,
    temperature: float = 0.7,
) -> Iterable[str]:
    """Streame la correction en text/plain char par char.

    - Emets les text_delta natifs de Claude
    - Garantit qu'un __END__JSON__ final est present (fallback si Claude l'oublie)
    - Si le modele refuse / sort vide, emet un JSON synthetique hors_sujet
      suivi de __END__JSON__ pour que le frontend parse toujours
    """
    emitted_any = False
    emitted_sentinel = False
    stop_reason: Optional[str] = None

    with _client.messages.stream(
        model=MODEL,
        max_tokens=max_tokens,
        temperature=temperature,
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

    if not emitted_any or stop_reason == "refusal":
        yield json.dumps(_refusal_payload(), ensure_ascii=False)
        yield "\n__END__JSON__"
        return

    if not emitted_sentinel:
        yield "\n__END__JSON__"


def generate_json(
    prompt: str,
    *,
    system: Optional[str] = None,
    max_tokens: int = 8192,
    temperature: float = 0.7,
    tache_identifiee: str = "",
) -> dict:
    """Appel non-streaming qui renvoie directement un dict.

    Utilise pour l'Expression Orale : on doit parser le JSON avant d'injecter
    l'URL audio dans le resultat. En cas de refus / JSON invalide / output vide,
    retourne un payload hors_sujet synthetique pour ne jamais casser l'appelant.
    """
    kwargs = dict(
        model=MODEL,
        max_tokens=max_tokens,
        temperature=temperature,
        messages=[{"role": "user", "content": prompt}],
    )
    if system:
        kwargs["system"] = system

    try:
        resp = _client.messages.create(**kwargs)
    except Exception as e:
        print(f"[Claude] generate_json error: {e}")
        return _refusal_payload(tache_identifiee)

    if resp.stop_reason == "refusal":
        return _refusal_payload(tache_identifiee)

    raw = "".join(
        b.text for b in resp.content if getattr(b, "type", None) == "text"
    ).strip()

    # Nettoyer un eventuel wrapper ```json ... ```
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
        if raw.endswith("```"):
            raw = raw[:-3].strip()

    # Extraire le premier bloc {...} si du texte parasite entoure
    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1 and end > start:
        raw = raw[start : end + 1]

    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"[Claude] JSON parse error: {e}\nRaw: {raw[:300]}")
        return _refusal_payload(tache_identifiee)


def chat_reply(
    *,
    system: str,
    messages: list,
    max_tokens: int = 400,
    temperature: float = 0.8,
) -> str:
    """Appel chat simple (Tache 2 Interaction) : renvoie juste la reponse texte."""
    try:
        resp = _client.messages.create(
            model=MODEL,
            system=system,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        if resp.stop_reason == "refusal":
            return "Excusez-moi, pouvez-vous reformuler votre demande ?"
        text = "".join(
            b.text for b in resp.content if getattr(b, "type", None) == "text"
        ).strip()
        return text or "Excusez-moi, pouvez-vous repeter s'il vous plait ?"
    except Exception as e:
        print(f"[Claude] chat_reply error: {e}")
        return "Excusez-moi, pouvez-vous repeter s'il vous plait ?"
