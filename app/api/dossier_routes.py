"""Lecture des pieces du dossier d'immigration.

## Ce que fait cette route, et ce qu'elle ne fait pas

Elle **lit** un document et rend des champs. Elle ne les valide pas,
ne les enregistre pas, et ne decide rien : c'est l'ecran qui fait
confirmer chaque ligne a la personne. Un numero de passeport lu a
80 %, ce n'est pas une donnee, c'est une question a poser.

C'est pour ca que chaque champ revient avec sa `confiance` et, quand
elle est basse, un `doute` dit en francais courant -- « 0 ou O ? ».
Un formulaire pre-rempli sans ce signal est pire qu'un formulaire
vide : on le survole, on valide, et l'erreur part chez IRCC.

## Pourquoi les champs sont dictes par l'appelant

Chaque piece du catalogue porte sa liste `champsIA`. Le passeport
demande sept champs, la lettre d'employeur en demande six dont les
taches. Coder cette liste ici obligerait a redeployer le service a
chaque piece ajoutee ; la recevoir la laisse en base, ou elle vit
deja avec le reste de la fiche.
"""
from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.ia.claude_client import lire_image_json

router = APIRouter(prefix="/dossier", tags=["dossier"])


class Cliche(BaseModel):
    data: str = Field(..., description="Image encodee en base64, sans prefixe")
    media_type: str = "image/jpeg"


class DemandeLecture(BaseModel):
    piece: str = Field(..., description="Identifiant de la piece, ex. passeport")
    titre: str = ""
    champs: list[str] = []
    images: list[Cliche] = []


SYSTEME = """Tu lis des documents officiels pour une demande de residence
permanente canadienne. Tu transcris, tu n'interpretes pas.

Regles absolues :
- N'invente jamais une valeur. Un champ absent ou illisible revient avec
  valeur vide et confiance "nulle".
- Ne corrige jamais ce que tu lis. Si le document porte une faute, garde
  la faute : c'est le document qui fait foi aupres d'IRCC, pas la
  vraisemblance.
- Les caracteres qui se confondent sont la premiere cause d'erreur :
  0 et O, 1 et I et l, 5 et S, 8 et B, 2 et Z. Des qu'un de ces couples
  est en jeu, la confiance tombe a "basse" et tu dis lequel dans
  `doute`.
- Les dates sortent au format AAAA-MM-JJ. Attention a l'ordre jour/mois :
  beaucoup de documents sont en JJ/MM/AAAA. Si l'ordre est ambigu --
  deux nombres inferieurs ou egaux a 12 -- confiance "basse" et dis-le.
- Les noms sortent tels qu'ecrits, accents compris, sans remettre de
  majuscules ou de minuscules.

Tu reponds uniquement par un objet JSON, sans texte autour :
{"champs": [{"cle": "...", "valeur": "...", "confiance": "haute|moyenne|basse|nulle", "doute": ""}],
 "pages": 1, "avertissement": ""}

`avertissement` sert a ce qui concerne le document entier et non un
champ : cliche coupe, reflet sur une zone, document visiblement
different de celui attendu."""


@router.post("/lire")
def lire(d: DemandeLecture) -> dict:
    """Lit les cliches d'une piece et renvoie ses champs."""
    if not d.images:
        return {"erreur": "aucune_image", "champs": []}

    champs = ", ".join(d.champs) if d.champs else "tous les champs lisibles"
    prompt = (
        f"Document attendu : {d.titre or d.piece}.\n"
        f"Champs a extraire, dans cet ordre : {champs}.\n"
        f"Nombre de cliches fournis : {len(d.images)}.\n\n"
        "Rends un champ par cle demandee, meme vide. N'ajoute aucune cle "
        "qui n'est pas demandee."
    )

    res = lire_image_json(
        images=[{"data": i.data, "media_type": i.media_type} for i in d.images],
        prompt=prompt,
        system=SYSTEME,
    )

    if "erreur" in res:
        return {"erreur": res["erreur"], "champs": []}

    # On renvoie exactement les cles demandees, dans l'ordre demande.
    # Le modele en oublie parfois une ; un champ manquant cote ecran
    # serait lu comme « rien a verifier », ce qui est l'inverse.
    lus = {c.get("cle"): c for c in res.get("champs", []) if isinstance(c, dict)}
    sortie = []
    for cle in (d.champs or list(lus)):
        c = lus.get(cle) or {}
        sortie.append({
            "cle": cle,
            "valeur": (c.get("valeur") or "").strip(),
            "confiance": c.get("confiance") or "nulle",
            "doute": (c.get("doute") or "").strip(),
        })

    return {
        "piece": d.piece,
        "champs": sortie,
        "pages": res.get("pages", len(d.images)),
        "avertissement": (res.get("avertissement") or "").strip(),
    }
