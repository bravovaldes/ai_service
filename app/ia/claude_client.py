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

_client: Optional[Anthropic] = None


def get_client() -> Anthropic:
    """Cree le client a la premiere utilisation, pas a l'import.

    Avant, `Anthropic(api_key=...)` s'executait au chargement du module.
    Une variable ANTHROPIC_API_KEY absente levait donc une exception AVANT
    qu'uvicorn n'ecoute : le conteneur ne demarrait pas et Render renvoyait
    502 sur TOUTES les routes, y compris /tcf/centres qui n'a rien a voir
    avec l'IA.

    En differant la creation, le service demarre toujours et seule la route
    concernee renvoie une erreur exploitable.
    """
    global _client
    if _client is None:
        cle = os.getenv("ANTHROPIC_API_KEY")
        if not cle:
            raise RuntimeError(
                "ANTHROPIC_API_KEY absente : la correction IA est indisponible."
            )
        _client = Anthropic(api_key=cle)
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


def _erreur_technique_payload() -> dict:
    """Distinct du refus : ici le modele n'a rien dit, c'est NOUS qui avons
    echoue. Le dire evite d'attribuer un 0/20 a un texte correct."""
    return {
        "niveau_estime": "",
        "points_forts": "",
        "points_faibles": "",
        "note_sur_20": None,
        "recommandation": (
            "La correction n'a pas abouti pour une raison technique. "
            "Ton texte n'est pas en cause : reessaie dans un moment."
        ),
        "erreur_technique": "oui",
        "modele_reponse": "",
    }


def _systeme_en_cache(system: Optional[str]):
    """Prepare le prompt systeme pour la mise en cache.

    Le bloc de calibrage des corrections ecrites — bareme, reperes de
    niveau, contrat de sortie — est identique d'une correction a l'autre.
    Il repartait pourtant en entier a chaque appel. Marque ainsi, l'API le
    garde et ne refacture au plein tarif que la partie variable : la
    consigne et le texte du candidat.

    Le seuil de mise en cache est d'environ 1024 jetons ; en dessous, la
    marque est simplement sans effet, jamais une erreur.
    """
    if not system:
        return None
    return [
        {
            "type": "text",
            "text": system,
            "cache_control": {"type": "ephemeral"},
        }
    ]


def stream_correction(
    prompt: str,
    *,
    system: Optional[str] = None,
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

    # Tout est capture : une exception levee ICI ne remonterait pas a
    # l'appelant. FastAPI a deja envoye l'en-tete 200 quand le flux demarre,
    # donc le client recevrait un 200 avec un corps VIDE et aucun message
    # d'erreur. C'est exactement ce qui s'est produit pendant deux mois apres
    # le passage du SDK en 1.x : « Messages.stream() got an unexpected keyword
    # argument 'temperature' », invisible cote application.
    try:
        parametres = dict(
            model=MODEL,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}],
        )
        bloc = _systeme_en_cache(system)
        if bloc:
            parametres["system"] = bloc

        with get_client().messages.stream(**parametres) as response:
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
    except Exception as e:
        print(f"[Claude] stream_correction error: {e}")
        if not emitted_any:
            # Charge utile exploitable par le frontend plutot qu'un corps vide.
            yield json.dumps(_erreur_technique_payload(), ensure_ascii=False)
            yield "\n__END__JSON__"
        return

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
    bloc = _systeme_en_cache(system)
    if bloc:
        kwargs["system"] = bloc

    try:
        resp = get_client().messages.create(**kwargs)
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
        resp = get_client().messages.create(
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


def lire_image_json(
    *,
    images: list,
    prompt: str,
    system: Optional[str] = None,
    max_tokens: int = 2048,
) -> dict:
    """Lit un ou plusieurs cliches d'un document et renvoie un dict.

    ## Pourquoi une fonction a part

    `generate_json` n'envoie que du texte. Un passeport n'est pas du
    texte : c'est une photo prise de travers, parfois avec un reflet,
    et c'est precisement la ou un modele se trompe. La difference
    n'est donc pas technique, elle est dans le contrat de sortie —
    chaque champ revient avec **son degre de certitude**, parce qu'un
    numero de passeport lu a 80 % n'est pas une donnee, c'est une
    question a poser.

    ## Temperature zero

    Sur une lecture, l'invention est le seul risque. On ne veut aucune
    variete : deux lectures du meme cliche doivent donner le meme
    resultat, sinon « Refaire » devient une loterie.

    `images` : liste de dicts {"media_type": "image/jpeg", "data": b64}.
    """
    contenu = []
    for im in images[:4]:   # quatre pages suffisent, et bornent le cout
        contenu.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": im.get("media_type", "image/jpeg"),
                "data": im["data"],
            },
        })
    contenu.append({"type": "text", "text": prompt})

    kwargs = dict(
        model=MODEL,
        max_tokens=max_tokens,
        temperature=0,
        messages=[{"role": "user", "content": contenu}],
    )
    bloc = _systeme_en_cache(system)
    if bloc:
        kwargs["system"] = bloc

    try:
        resp = get_client().messages.create(**kwargs)
    except Exception as e:
        print(f"[Claude] lire_image_json error: {e}")
        return {"erreur": "technique"}

    if resp.stop_reason == "refusal":
        return {"erreur": "refus"}

    raw = "".join(
        b.text for b in resp.content if getattr(b, "type", None) == "text"
    ).strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
        if raw.endswith("```"):
            raw = raw[:-3].strip()
    start, end = raw.find("{"), raw.rfind("}")
    if start != -1 and end != -1 and end > start:
        raw = raw[start:end + 1]
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"[Claude] lecture JSON invalide: {e}\nRaw: {raw[:300]}")
        return {"erreur": "illisible"}
