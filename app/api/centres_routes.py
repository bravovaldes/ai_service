# app/api/tcf_routes.py

import re
import time
import json
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup
from fastapi import APIRouter, Query, HTTPException

router = APIRouter(prefix="/tcf", tags=["TCF"])

BASE = "https://www.france-education-international.fr"
LISTE_URL = f"{BASE}/centres-d-examen/liste"
UA = "Mozilla/5.0 (compatible; TCF-Scraper/1.3; +https://example.com/bot)"
HEADERS = {"User-Agent": UA}

# Liste ajustable des pays “francophones”
FRANCOPHONES = {
    "France", "Belgique", "Suisse", "Luxembourg", "Canada", "Monaco",
    "Cameroun", "Côte d’Ivoire", "Côte d'Ivoire", "Sénégal", "Mali", "Niger",
    "Burkina Faso", "Togo", "Bénin", "Guinée", "Guinée-Bissau", "Tchad",
    "République centrafricaine", "Centrafrique", "Congo", "République du Congo",
    "RDC", "République démocratique du Congo", "Gabon", "Djibouti", "Comores",
    "Madagascar", "Seychelles", "Mauritanie", "Maroc", "Algérie", "Tunisie",
    "Haïti", "Liban", "Vanuatu", "Burundi", "Rwanda", "Maurice"
}

# --- petit cache mémoire (TTL) pour éviter de frapper trop souvent le site
@dataclass
class CacheEntry:
    data: object
    expires_at: datetime

CACHE: Dict[str, CacheEntry] = {}
DEFAULT_TTL = timedelta(minutes=30)


def _cache_get(key: str):
    entry = CACHE.get(key)
    if not entry:
        return None
    if entry.expires_at < datetime.utcnow():
        CACHE.pop(key, None)
        return None
    return entry.data


def _cache_set(key: str, data, ttl: timedelta = DEFAULT_TTL):
    CACHE[key] = CacheEntry(data=data, expires_at=datetime.utcnow() + ttl)


def _soup(html: str) -> BeautifulSoup:
    # lxml si dispo, sinon fallback sur html.parser
    try:
        return BeautifulSoup(html, "lxml")
    except Exception:
        return BeautifulSoup(html, "html.parser")


def get_country_id_map(session: requests.Session) -> Dict[str, str]:
    """
    Lit le <select class="map-filter" data-get-param="pays"> de la page /liste?type-centre=tcf
    Chaque <option> a une value = URL comme '/centres-d-examen/liste?pays=112&type-centre=tcf'
    → on en extrait l'ID numérique.
    """
    r = session.get(f"{LISTE_URL}?type-centre=tcf", headers=HEADERS, timeout=60)
    r.raise_for_status()
    soup = _soup(r.text)

    sel = soup.select_one('select.map-filter.form-select[data-get-param="pays"]')
    if not sel:
        return {}

    country_id_map: Dict[str, str] = {}
    for opt in sel.find_all("option"):
        label = (opt.get_text() or "").strip()
        href = opt.get("value", "")
        m = re.search(r"[?&]pays=(\d+)", href)
        if label and m:
            country_id_map[label] = m.group(1)
    return country_id_map


def clean_text(node) -> str:
    if not node:
        return ""
    txt = node.get_text(" ", strip=True)
    return re.sub(r"\s+", " ", txt).strip()


def parse_cards_from_page(html: str) -> List[Dict]:
    soup = _soup(html)
    centers: List[Dict] = []
    for article in soup.select("div.item-list li article"):
        country = clean_text(article.select_one(".field--name-field-pays h4.title"))
        title = clean_text(article.find("h2"))
        address = clean_text(article.select_one(".field--name-field-adresse-complete"))

        phone_a = article.select_one('.field--name-field-telephone a[href^="tel:"]')
        email_a = article.select_one('.field--name-field-email a[href^="mailto:"]')
        site_a = article.select_one(".field--name-field-site-web a")

        phone = phone_a.get_text(strip=True) if phone_a else ""
        email = email_a.get_text(strip=True) if email_a else ""
        website = site_a.get("href") if site_a else ""

        sessions_pc = article.select_one("div.option-sessions-ordi") is not None

        centers.append(
            {
                "country": country,
                "title": title,
                "address": address,
                "phone": phone,
                "email": email,
                "website": website,
                "sessions_on_computer": sessions_pc,
            }
        )
    return centers


def fetch_country_centers(session: requests.Session, country_id: str) -> Tuple[str, List[Dict]]:
    url = f"{LISTE_URL}?pays={country_id}&type-centre=tcf"
    r = session.get(url, headers=HEADERS, timeout=60)
    r.raise_for_status()
    centers = parse_cards_from_page(r.text)
    # Deviner le nom du pays depuis la 1ère carte (si dispo)
    country_name = centers[0]["country"] if centers else ""
    for c in centers:
        c["source"] = url
        c["country_id"] = country_id
    return country_name, centers


@router.get("/centres")
def get_tcf_centers(
    francophones: bool = Query(
        False, description="Limiter aux pays francophones (liste interne)."
    ),
    countries: List[str] = Query(
        default_factory=list,
        description="Noms exacts de pays à inclure (ex: Canada, Cameroun).",
    ),
    refresh: bool = Query(
        False, description="Ignorer le cache et rafraîchir maintenant."
    ),
    delay: float = Query(
        0.8, ge=0.0, le=3.0, description="Délai de politesse entre requêtes (secondes)."
    ),
):
    """
    Scrape officiel FEI (page publique) pour lister les **centres TCF**.

    - `francophones=true` : ignore `countries` et utilise une liste de pays FR interne
    - `countries=['Canada','Cameroun']` : filtre explicite par noms (doivent correspondre au menu)
    - `refresh=true` : force le refetch côté serveur
    """
    cache_key = json.dumps(
        {"fr": francophones, "co": sorted(countries), "d": delay}, sort_keys=True
    )

    if not refresh:
        cached = _cache_get(cache_key)
        if cached is not None:
            return cached

    try:
        session = requests.Session()
        country_map = get_country_id_map(session)
        if not country_map:
            raise HTTPException(
                status_code=502,
                detail="Impossible de détecter la liste des pays sur la page FEI.",
            )

        # Déterminer la cible de pays
        if francophones:
            target_names = [
                name
                for name in country_map.keys()
                if any(fr.lower() in name.lower() for fr in FRANCOPHONES)
            ]
        elif countries:
            # garder seulement ceux présents dans le menu
            target_names = [c for c in countries if c in country_map]
            unknown = [c for c in countries if c not in country_map]
            if unknown:
                # On n'arrête pas mais on le signale dans la réponse
                pass
        else:
            # Par défaut : tous les pays du menu (long !)
            target_names = list(country_map.keys())

        results: List[Dict] = []
        errors: List[Dict] = []

        for name in sorted(target_names):
            cid = country_map.get(name)
            if not cid:
                errors.append({"country": name, "error": "ID introuvable"})
                continue
            try:
                _, centers = fetch_country_centers(session, cid)
                # Surcharge avec le nom du menu (plus stable)
                for c in centers:
                    c["country"] = name
                results.extend(centers)
                if delay:
                    time.sleep(delay)
            except requests.HTTPError as e:
                errors.append({"country": name, "error": f"HTTP {e.response.status_code}"})
            except Exception as e:
                errors.append({"country": name, "error": str(e)})

        payload = {
            "count": len(results),
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "francophones": francophones,
            "countries": target_names,
            "errors": errors,
            "items": results,
            "source": LISTE_URL + "?type-centre=tcf",
            "legal_note": "Source ©france-education-international.fr – usage conforme au robots.txt, sans iframe.",
        }

        _cache_set(cache_key, payload)
        return payload

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Erreur FEI: {e.__class__.__name__}: {e}",
        )
