"""Transcription enrichie de l'audio du candidat, via ElevenLabs Scribe.

Pourquoi ce module existe.

Jusqu'ici l'expression orale etait transcrite SUR LE TELEPHONE par le greffon
`speech_to_text`, qui ne rend qu'une chaine de mots : ni temps, ni confiance,
ni hesitations. Claude corrigeait donc un texte appauvri en croyant corriger
une production orale — d'ou les trente lignes du prompt qui lui demandent
d'ignorer des fautes inventees par la transcription, et d'ou le plafond
observe a 13/20 alors que l'ecrit atteint 19/20.

On ne peut pas envoyer l'audio a Claude : l'API accepte le texte, l'image et
le document, pas le son. En revanche Scribe rend les temps mot a mot, les
disfluences et un indice de confiance. De quoi calculer ce qui manquait —
debit, pauses, hesitations — et le donner au correcteur.

Ce n'est pas equivalent a entendre le candidat. Mais cela rend mesurables la
fluidite et l'aisance, qui sont exactement les criteres ou se joue le passage
de B2 a C1, et qu'un texte brut rend invisibles.
"""
import os
from dataclasses import dataclass, field
from typing import Optional

import requests

API = "https://api.elevenlabs.io/v1/speech-to-text"

# Marqueurs d'hesitation en francais parle. Scribe les conserve quand on ne
# demande pas de nettoyage — c'est precisement ce qu'on veut ici.
HESITATIONS = {"euh", "euhm", "heu", "hum", "hmm", "ben", "bah", "mmh"}

# Seuil a partir duquel un silence compte comme une pause marquee. En dessous
# c'est une respiration normale, au-dessus c'est une recherche de mot.
PAUSE_MIN = 0.8


@dataclass
class Prosodie:
    """Ce que le texte seul ne dit pas."""

    duree: float = 0.0
    nb_mots: int = 0
    debit: float = 0.0            # mots par minute
    nb_hesitations: int = 0
    nb_pauses: int = 0
    pause_max: float = 0.0
    temps_parle: float = 0.0      # hors silences
    repetitions: int = 0

    @property
    def taux_hesitation(self) -> float:
        return round(100 * self.nb_hesitations / self.nb_mots, 1) if self.nb_mots else 0.0

    @property
    def taux_silence(self) -> float:
        return round(100 * (1 - self.temps_parle / self.duree), 1) if self.duree else 0.0

    def resume(self) -> str:
        """Formulation destinee au correcteur, en clair plutot qu'en JSON.

        Volontairement descriptive et non interpretee : c'est au modele de
        juger si 95 mots/minute est lent pour le niveau vise, pas a nous.
        """
        return (
            f"- Duree de la production : {self.duree:.0f} secondes\n"
            f"- Debit : {self.debit:.0f} mots par minute "
            f"(un locuteur francais a l'aise tourne autour de 140-160)\n"
            f"- Temps de silence : {self.taux_silence:.0f} % de la duree\n"
            f"- Pauses marquees (plus de {PAUSE_MIN} s) : {self.nb_pauses}"
            f"{f', la plus longue de {self.pause_max:.1f} s' if self.nb_pauses else ''}\n"
            f"- Hesitations audibles (euh, ben...) : {self.nb_hesitations} "
            f"soit {self.taux_hesitation} % des mots\n"
            f"- Repetitions immediates d'un mot : {self.repetitions}"
        )


@dataclass
class Transcription:
    texte: str
    prosodie: Prosodie
    mots_peu_surs: list = field(default_factory=list)

    def pour_le_client(self) -> dict:
        """Ce qu'on montre a l'utilisateur.

        Il doit pouvoir verifier ce que le correcteur a REELLEMENT entendu :
        la transcription faite sur son telephone est souvent fautive — elle
        a rendu « Valdez bravo » par « Valdez bravo maison » — et lui
        montrer ce texte-la comme etant sa reponse est trompeur.

        Les mesures de fluidite sont incluses pour la meme raison : une note
        qui parle de debit sans montrer le debit n'est pas verifiable.
        """
        p = self.prosodie
        return {
            "transcription": self.texte,
            "duree_secondes": round(p.duree, 1),
            "nb_mots": p.nb_mots,
            "debit_mots_minute": round(p.debit),
            "taux_silence": p.taux_silence,
            "nb_pauses": p.nb_pauses,
            "pause_max": round(p.pause_max, 1),
            "nb_hesitations": p.nb_hesitations,
            "taux_hesitation": p.taux_hesitation,
            "repetitions": p.repetitions,
            "mots_peu_surs": self.mots_peu_surs[:12],
        }

    def indice_prononciation(self) -> str:
        """Les mots que la transcription a mal reconnus.

        Un mot rendu avec une faible confiance signale souvent une
        prononciation approximative. C'est un INDICE, jamais une preuve :
        le bruit de fond produit le meme effet. Le correcteur doit en tenir
        compte avec prudence, et on le lui dit.
        """
        if not self.mots_peu_surs:
            return "- Aucun mot mal reconnu : prononciation probablement claire."
        apercu = ", ".join(f'"{m}"' for m in self.mots_peu_surs[:12])
        return (
            f"- Mots mal reconnus par la transcription ({len(self.mots_peu_surs)}) : "
            f"{apercu}\n"
            "  Indice possible d'une prononciation approximative, mais le bruit "
            "de fond produit le meme effet : a manier avec prudence."
        )


def transcrire(contenu: bytes, nom: str = "audio.m4a") -> Optional[Transcription]:
    """Transcrit l'audio et en extrait la prosodie. `None` si l'appel echoue."""
    cle = os.getenv("ELEVENLABS_API_KEY")
    if not cle:
        return None
    try:
        r = requests.post(
            API,
            headers={"xi-api-key": cle},
            files={"file": (nom, contenu)},
            data={
                "model_id": "scribe_v1",
                "language_code": "fra",
                # On NE nettoie PAS les disfluences : les « euh » sont
                # justement ce qu'on veut mesurer.
                "tag_audio_events": "false",
                "timestamps_granularity": "word",
            },
            timeout=120,
        )
        r.raise_for_status()
        return _analyser(r.json())
    except Exception as e:
        print(f"[Scribe] erreur: {e}")
        return None


def _analyser(brut: dict) -> Transcription:
    mots = [m for m in brut.get("words", []) if m.get("type") == "word"]
    texte = (brut.get("text") or "").strip()

    p = Prosodie(nb_mots=len(mots))
    if not mots:
        return Transcription(texte=texte, prosodie=p)

    p.duree = float(mots[-1].get("end", 0)) - float(mots[0].get("start", 0))
    if p.duree > 0:
        p.debit = p.nb_mots / p.duree * 60

    peu_surs, precedent_fin, precedent_mot = [], None, None
    for m in mots:
        deb, fin = float(m.get("start", 0)), float(m.get("end", 0))
        p.temps_parle += max(0.0, fin - deb)

        if precedent_fin is not None:
            silence = deb - precedent_fin
            if silence >= PAUSE_MIN:
                p.nb_pauses += 1
                p.pause_max = max(p.pause_max, silence)
        precedent_fin = fin

        brut_mot = (m.get("text") or "").strip().lower().strip(".,!?;:")
        if brut_mot in HESITATIONS:
            p.nb_hesitations += 1
        # Repetition immediate : « je je pense », signe d'une reformulation
        # en cours, que la note doit distinguer d'un vrai blocage.
        if brut_mot and brut_mot == precedent_mot:
            p.repetitions += 1
        precedent_mot = brut_mot

        c = m.get("logprob")
        if c is not None and c < -1.0 and brut_mot not in HESITATIONS:
            peu_surs.append(m.get("text"))

    return Transcription(texte=texte, prosodie=p, mots_peu_surs=peu_surs)
