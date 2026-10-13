"""Le FEER se deduit du code, il ne se croit pas.

Dans la CNP 2021, le deuxieme chiffre du code a cinq chiffres **est**
la categorie FEER (verifie sur statcan.gc.ca le 12 oct. 2026). C'est
le champ qui decide si une experience compte : FEER 0 a 3 oui, 4 et 5
non. Une erreur d'un rang ouvre ou ferme les trois programmes.
"""
from app.api.dossier_routes import _feer_du_code


def test_le_deuxieme_chiffre_donne_le_feer():
    assert _feer_du_code("11100") == 1   # comptables
    assert _feer_du_code("12200") == 2   # techniciens en comptabilite
    assert _feer_du_code("63200") == 3   # cuisiniers
    assert _feer_du_code("65100") == 5   # caissiers
    assert _feer_du_code("00010") == 0   # legislateurs


def test_un_code_mal_forme_est_jete_et_non_corrige():
    # Mieux vaut aucune suggestion qu'une suggestion rafistolee : on
    # ne devine pas un code d'immigration.
    assert _feer_du_code("1110") is None      # quatre chiffres
    assert _feer_du_code("111000") is None    # six
    assert _feer_du_code("A1100") is None     # une lettre
    assert _feer_du_code("") is None


def test_un_feer_hors_bareme_est_refuse():
    # Le barreme s'arrete a 5. Un « 6 » en deuxieme position n'existe
    # pas dans la CNP, donc le code est faux.
    assert _feer_du_code("16100") is None
    assert _feer_du_code("19100") is None


# ── L'enonce principal, et la plupart des taches ──────────────
#
# IRCC demande deux choses, pas une : « the actions in the lead
# statement of the NOC job description, AND most of the main duties
# listed » (canada.ca, Experience canadienne, verifie le 13 oct.
# 2026). Un metier propose sur deux taches qui se recoupent est
# exactement ce qui fait refuser un dossier des mois plus tard --
# « compte des caisses » se retrouve chez l'equipier comme chez le
# superviseur.
from app.api.dossier_routes import _propre


def _m(**kw):
    base = {"code": "62020", "titre": "Superviseurs", "enonce": "Supervise",
            "enonceAccompli": True, "couvertes": ["a", "b", "c"],
            "manquantes": ["d"]}
    return {**base, **kw}


def test_le_metier_principal_exige_l_enonce_accompli():
    assert _propre(_m(), exiger_enonce=True) is not None
    assert _propre(_m(enonceAccompli=False), exiger_enonce=True) is None


def test_le_metier_principal_exige_la_majorite_des_taches():
    # Trois sur quatre : retenu.
    assert _propre(_m(), exiger_enonce=True) is not None
    # Deux sur quatre : la moitie n'est pas « la plupart ».
    assert _propre(_m(couvertes=["a", "b"], manquantes=["c", "d"]),
                   exiger_enonce=True) is None
    # Une sur cinq : refuse.
    assert _propre(_m(couvertes=["a"], manquantes=["b", "c", "d", "e"]),
                   exiger_enonce=True) is None


def test_un_metier_proche_s_affiche_meme_incomplet():
    # Les proches sont des pistes : « celui-ci te va si tu as aussi
    # fait ceci ». Les taire priverait de la seule comparaison utile.
    p = _propre(_m(enonceAccompli=False, couvertes=["a"],
                   manquantes=["b", "c"]), exiger_enonce=False)
    assert p is not None
    assert p["manquantes"] == ["b", "c"]
    assert p["enonceAccompli"] is False


def test_le_feer_reste_deduit_du_code_et_non_du_modele():
    p = _propre(_m(feer=0), exiger_enonce=True)
    assert p["feer"] == 2   # 62020 : deuxieme chiffre


def test_sans_decoupage_des_taches_on_ne_bloque_pas():
    # Un modele qui ne rend ni couvertes ni manquantes ne doit pas
    # faire disparaitre la suggestion : l'enonce accompli suffit, et
    # l'ecran affichera simplement le metier sans le detail.
    p = _propre(_m(couvertes=[], manquantes=[]), exiger_enonce=True)
    assert p is not None


from app.api.dossier_routes import _pourquoi_refuse


def test_on_dit_pourquoi_rien_n_est_retenu():
    # « Aucun metier trouve » apres avoir decrit ses journees ne dit ni
    # si l'application a echoue, ni ce qu'il faut corriger.
    sans_enonce = _pourquoi_refuse(_m(enonceAccompli=False))
    assert "n'y est pas decrit" in sans_enonce

    trop_peu = _pourquoi_refuse(
        _m(couvertes=["a"], manquantes=["b", "c", "d"]))
    assert "1 des 4 taches" in trop_peu


def test_sans_detail_on_n_invente_pas_de_raison():
    assert _pourquoi_refuse(_m(couvertes=[], manquantes=[])) == ""
    assert _pourquoi_refuse(None) == ""
