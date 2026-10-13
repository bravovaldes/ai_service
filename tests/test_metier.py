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
