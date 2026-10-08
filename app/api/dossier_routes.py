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
    controles: list[str] = []
    images: list[Cliche] = []

    # Pour les controles qui comparent a autre chose qu'au document :
    # le nom du passeport deja lu, et la date de depot envisagee.
    nom_reference: str = ""
    depot_prevu: str = ""


# Ce que chaque code de controle demande de verifier. Le libelle vit
# dans l'application ; ici on ne decrit que la regle, parce que c'est
# elle qui doit etre dite au modele.
REGLES = {
    "texte": "Le document est lisible et le texte a pu etre lu en entier.",
    "nom": ("Le nom porte sur le document correspond au nom de reference "
            "fourni. Une difference d'accent ou d'ordre prenom/nom n'est "
            "pas un probleme ; un nom different l'est."),
    "dateDelivrance": ("La date de delivrance : le document doit avoir "
                       "moins de 6 mois a la date de depot prevue."),
    "dateExpiration": ("La date d'expiration : le document doit etre "
                       "encore valide, et de preference plus de 6 mois."),
    "dateTest": "La date du test : les resultats valent deux ans.",
    "dateRapport": "La date du rapport : il vaut cinq ans.",
    "dateExamen": "La date de l'examen : il vaut douze mois.",
    "dateNomination": "La nomination doit etre encore valide.",
    "dateBiometrie": "La biometrie vaut dix ans.",
    "dateLettre": "La lettre de banque doit avoir moins de 6 mois.",
    "langue": ("La langue du document. En francais ou en anglais : rien "
               "a faire. Dans une autre langue : une traduction certifiee "
               "sera exigee."),
    "tampon": "Un tampon officiel et une signature sont presents.",
    "montant": ("Le solde et la moyenne sur six mois figurent, ainsi que "
                "les dettes."),
    "taches": ("Les taches du poste sont decrites. Sans elles, le code "
               "CNP ne peut pas etre confirme."),
    "scores": "Les quatre scores des quatre epreuves figurent.",
    "dates": "Les dates de debut et de fin figurent.",
    "equivalence": "L'equivalence canadienne du diplome est indiquee.",
}


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
 "controles": [{"code": "...", "ok": true, "constat": "", "consequence": ""}],
 "pages": 1, "avertissement": ""}

Pour chaque controle demande :
- `ok` : vrai si la regle est respectee.
- `constat` : ce que tu as vu, en une phrase courte et factuelle --
  « Delivre le 12 janvier 2026 », « En francais ».
- `consequence` : seulement quand `ok` est faux, ce que ca entraine
  pour le dossier, en une phrase. Pas de conseil, pas de ton alarmiste :
  le fait et sa suite.

Un controle que le document ne permet pas de trancher revient avec
`ok` a faux et un constat qui dit pourquoi. Ne devine pas.

`avertissement` sert a ce qui concerne le document entier et non un
champ : cliche coupe, reflet sur une zone, document visiblement
different de celui attendu."""


@router.post("/lire")
def lire(d: DemandeLecture) -> dict:
    """Lit les cliches d'une piece et renvoie ses champs."""
    if not d.images:
        return {"erreur": "aucune_image", "champs": []}

    champs = ", ".join(d.champs) if d.champs else "tous les champs lisibles"
    lignes = [
        f"Document attendu : {d.titre or d.piece}.",
        f"Champs a extraire, dans cet ordre : {champs}.",
        f"Nombre de cliches fournis : {len(d.images)}.",
    ]
    if d.nom_reference:
        lignes.append(f"Nom de reference (passeport) : {d.nom_reference}.")
    if d.depot_prevu:
        lignes.append(f"Date de depot prevue : {d.depot_prevu}.")
    if d.controles:
        lignes.append("")
        lignes.append("Controles a rendre, dans cet ordre :")
        for c in d.controles:
            lignes.append(f"- {c} : {REGLES.get(c, c)}")
    lignes.append("")
    lignes.append("Rends un champ par cle demandee, meme vide. N'ajoute "
                  "aucune cle qui n'est pas demandee.")
    prompt = "\n".join(lignes)

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

    # Les controles, dans l'ordre demande et jamais inventes : un
    # controle absent de la reponse est un controle **non passe**, pas
    # un controle reussi. L'inverse ferait afficher un vert mensonger.
    rendus = {c.get("code"): c for c in res.get("controles", [])
              if isinstance(c, dict)}
    controles = []
    for code in d.controles:
        c = rendus.get(code) or {}
        controles.append({
            "code": code,
            "ok": bool(c.get("ok")) if "ok" in c else False,
            "constat": (c.get("constat") or "").strip()
                       or "Pas verifiable sur ce cliche",
            "consequence": (c.get("consequence") or "").strip(),
        })

    return {
        "piece": d.piece,
        "champs": sortie,
        "controles": controles,
        "pages": res.get("pages", len(d.images)),
        "avertissement": (res.get("avertissement") or "").strip(),
    }
