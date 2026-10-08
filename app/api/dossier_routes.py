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
import datetime as _dt

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


# ── Les dates ne passent pas par le modele ───────────────────
#
# Un modele de langue sait lire « 12 janvier 2026 ». Il ne sait pas
# fiablement dire combien de mois separent cette date du 6 janvier
# 2027 : teste, il a repondu « moins de 6 mois » -- et valide ainsi un
# certificat qui aurait fait refuser le dossier.
#
# Le partage est donc strict : le modele **lit**, le code **juge**.
# Chaque controle de date nomme son champ source et sa duree de
# validite en mois ; le reste est de l'arithmetique.
#
# code : (champ source, validite en mois, libelle)
DATES = {
    "dateDelivrance": ("delivreLe", 6, "Delivre"),
    "dateTest": ("dateTest", 24, "Passe"),
    "dateRapport": ("dateRapport", 60, "Etabli"),
    "dateExamen": ("dateExamen", 12, "Passe"),
    "dateLettre": ("dateLettre", 6, "Etablie"),
    "dateBiometrie": ("dateBiometrie", 120, "Donnee"),
}
MOIS_FR = ["janvier", "fevrier", "mars", "avril", "mai", "juin", "juillet",
           "aout", "septembre", "octobre", "novembre", "decembre"]


def _jour(d: _dt.date) -> str:
    return f"{d.day} {MOIS_FR[d.month - 1]} {d.year}"


def _ajouter_mois(d: _dt.date, mois: int) -> _dt.date:
    m = d.month - 1 + mois
    an = d.year + m // 12
    m = m % 12 + 1
    # Le 31 mars moins un mois n'existe pas en fevrier : on recule au
    # dernier jour valide plutot que de lever.
    jour = min(d.day, [31, 29 if an % 4 == 0 and (an % 100 or an % 400 == 0)
                       else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m - 1])
    return _dt.date(an, m, jour)


def _controle_date(code: str, valeurs: dict, depot: _dt.date | None) -> dict:
    champ, mois, verbe = DATES[code]
    brut = (valeurs.get(champ) or "").strip()
    try:
        d = _dt.date.fromisoformat(brut)
    except ValueError:
        return {"code": code, "ok": False,
                "constat": "Date non lue sur ce cliche",
                "consequence": "Sans elle, impossible de verifier la validite."}

    limite = _ajouter_mois(d, mois)
    if depot is None:
        depot = _dt.date.today()
    ok = limite >= depot
    an = mois // 12
    duree = f"{an} an{'s' if an > 1 else ''}" if mois % 12 == 0 and mois >= 12 \
        else f"{mois} mois"
    return {
        "code": code,
        "ok": ok,
        "constat": f"{verbe} le {_jour(d)}",
        "consequence": "" if ok else
        f"Valable {duree}, donc perime le {_jour(limite)} : "
        f"il sera trop ancien au depot prevu le {_jour(depot)}.",
    }


def _controle_expiration(valeurs: dict, depot: _dt.date | None) -> dict:
    brut = (valeurs.get("expireLe") or "").strip()
    try:
        d = _dt.date.fromisoformat(brut)
    except ValueError:
        return {"code": "dateExpiration", "ok": False,
                "constat": "Date d'expiration non lue",
                "consequence": "Sans elle, impossible de verifier la validite."}
    if depot is None:
        depot = _dt.date.today()
    # Six mois de marge apres le depot : un visa ne peut pas depasser
    # l'expiration du passeport, et la procedure continue apres.
    ok = d >= _ajouter_mois(depot, 6)
    return {
        "code": "dateExpiration",
        "ok": ok,
        "constat": f"Expire le {_jour(d)}",
        "consequence": "" if ok else
        f"Il doit rester valide au moins six mois apres le depot prevu "
        f"le {_jour(depot)}. Renouvelle-le avant de deposer.",
    }


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
    # Seuls les controles que le modele peut trancher lui sont poses.
    pour_modele = [c for c in d.controles
                   if c not in DATES and c != "dateExpiration"]
    if pour_modele:
        lignes.append("")
        lignes.append("Controles a rendre, dans cet ordre :")
        for c in pour_modele:
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
    valeurs = {c["cle"]: c["valeur"] for c in sortie}
    try:
        depot = _dt.date.fromisoformat(d.depot_prevu) if d.depot_prevu else None
    except ValueError:
        depot = None

    controles = []
    for code in d.controles:
        if code in DATES:
            controles.append(_controle_date(code, valeurs, depot))
            continue
        if code == "dateExpiration":
            controles.append(_controle_expiration(valeurs, depot))
            continue
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
