"""
Cyber-Tech Prospection — Scraper automatisé des offres de formation cybersécurité IDF

Ce script utilise Playwright pour scraper:
1. LinkedIn Jobs (formateur cybersécurité, intervenant vacataire, etc.)
2. Welcome to the Jungle
3. Les formateurs.com

Usage:
    python3 scripts/scraper_jobs.py          # Scraper toutes les sources
    python3 scripts/scraper_jobs.py --sources linkedin,wttj  # Sources spécifiques
    python3 scripts/scraper_jobs.py --update  # Scraper + fusionner dans offres.json
"""

import json
import os
import re
import sys
import time
from datetime import datetime
from urllib.parse import quote

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
OFFRES_JSON = os.path.join(DATA_DIR, "offres.json")

# ── Configuration ──────────────────────────────────────────────────────────
SOURCES = ["linkedin", "wttj"]  # Lesformateurs.com inaccessible

QUERIES = [
    "formateur cybersécurité",
    "intervenant vacataire sécurité informatique",
    "chargé de cours cybersécurité",
    "formateur SOC",
    "formateur RSSI",
]

SCHOOL_SOURCES = [
    # Pages carrières des écoles — format: (nom, url, sélecteur offre)
    ("IPSA (IONIS)", "https://careers.werecruit.io/fr/ionis-group/offres", None),
    ("EPITA", "https://www.epita.fr/recrutement/", None),
]


def extract_with_playwright():
    """
    Scrape les job boards avec Playwright.
    Retourne une liste d'offres (dict).
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("❌ Playwright non installé. Installe avec:")
        print("   pip install --break-system-packages playwright")
        print("   playwright install chromium --with-deps")
        return []

    all_offers = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            locale="fr-FR",
            timezone_id="Europe/Paris",
        )
        page = context.new_page()

        # ── LinkedIn ─────────────────────────────────────────────────────
        for query in QUERIES:
            print(f"\n🔍 LinkedIn: {query}")
            try:
                encoded_q = quote(query)
                url = f"https://fr.linkedin.com/jobs/search/?keywords={encoded_q}&location=%C3%8Ele-de-France"
                page.goto(url, timeout=30000, wait_until="domcontentloaded")
                time.sleep(3)

                # Scroll for lazy loading
                for _ in range(3):
                    page.evaluate("window.scrollBy(0, 500)")
                    time.sleep(1)

                # Try to extract job cards
                jobs = page.evaluate("""
                    () => {
                        const cards = document.querySelectorAll('.job-card-container, .job-search-card');
                        const results = [];
                        cards.forEach(card => {
                            const title = card.querySelector('.job-card-list__title, .job-search-card__title');
                            const company = card.querySelector('.job-card-container__company-name, .job-search-card__subtitle');
                            const location = card.querySelector('.job-card-container__metadata-wrapper, .job-search-card__location');
                            const link = card.querySelector('a');
                            results.push({
                                title: title ? title.innerText.trim() : '',
                                company: company ? company.innerText.trim() : '',
                                location: location ? location.innerText.trim() : '',
                                url: link ? link.href : ''
                            });
                        });
                        return results;
                    }
                """)

                for job in jobs:
                    if job.get("title") and any(k.lower() in job["title"].lower() for k in ["cyber", "sécurité", "security", "réseau"]):
                        offer = {
                            "titre": job["title"],
                            "etablissement": job.get("company", ""),
                            "type_mission": "Vacation/CDD (à confirmer)",
                            "matieres": "Cybersécurité",
                            "niveau": "Non précisé",
                            "localisation": job.get("location", "Île-de-France"),
                            "date_publication": datetime.now().strftime("%Y-%m-%d"),
                            "date_limite": "",
                            "url": job.get("url", ""),
                            "email_contact": "",
                            "statut": "Non contacté",
                            "source": "linkedin",
                            "notes": f'Trouvé via "{query}" sur LinkedIn'
                        }
                        all_offers.append(offer)
                        print(f"   ✅ {job['title'][:60]} — {job.get('company','?')}")

            except Exception as e:
                print(f"   ⚠️  Erreur LinkedIn ({query}): {e}")

        # ── Welcome to the Jungle ────────────────────────────────────────
        for query in QUERIES[:3]:
            print(f"\n🔍 Welcome to the Jungle: {query}")
            try:
                encoded_q = quote(query)
                url = f"https://www.welcometothejungle.com/fr/jobs?query={encoded_q}&location=%C3%8Ele-de-France"
                page.goto(url, timeout=30000, wait_until="domcontentloaded")
                time.sleep(3)

                jobs = page.evaluate("""
                    () => {
                        const cards = document.querySelectorAll('[data-testid="job-card"], .sc-job-card, article');
                        const results = [];
                        cards.forEach(card => {
                            const title = card.querySelector('h2, h3, [class*="title"]');
                            const company = card.querySelector('[class*="company"], [class*="organization"]');
                            const location = card.querySelector('[class*="location"]');
                            const link = card.querySelector('a[href*="/jobs/"]');
                            results.push({
                                title: title ? title.innerText.trim() : '',
                                company: company ? company.innerText.trim() : '',
                                location: location ? location.innerText.trim() : '',
                                url: link ? link.href : ''
                            });
                        });
                        return results;
                    }
                """)

                for job in jobs:
                    if job.get("title"):
                        offer = {
                            "titre": job["title"],
                            "etablissement": job.get("company", ""),
                            "type_mission": "Vacation/CDD (à confirmer)",
                            "matieres": "Cybersécurité",
                            "niveau": "Non précisé",
                            "localisation": job.get("location", "Île-de-France"),
                            "date_publication": datetime.now().strftime("%Y-%m-%d"),
                            "date_limite": "",
                            "url": job.get("url", ""),
                            "email_contact": "",
                            "statut": "Non contacté",
                            "source": "wttj",
                            "notes": f'Trouvé via "{query}" sur WTTJ'
                        }
                        all_offers.append(offer)
                        print(f"   ✅ {job['title'][:60]}")

            except Exception as e:
                print(f"   ⚠️  Erreur WTTJ ({query}): {e}")

        browser.close()

    return all_offers


def load_existing_offers():
    """Charge les offres existantes depuis le JSON."""
    if os.path.exists(OFFRES_JSON):
        with open(OFFRES_JSON, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def merge_offers(existing, new_offers):
    """Fusionne les nouvelles offres (évite les doublons par URL)."""
    existing_urls = {o.get("url", "") for o in existing if o.get("url")}
    merged = list(existing)

    for offer in new_offers:
        if offer.get("url") and offer["url"] not in existing_urls:
            merged.append(offer)
            existing_urls.add(offer["url"])
            print(f"   ➕ Nouvelle offre: {offer['titre'][:60]}")
        elif offer.get("url"):
            print(f"   ⏩ Déjà existante: {offer['titre'][:60]}")

    return merged


def save_offers(offers):
    """Sauvegarde les offres dans le JSON."""
    with open(OFFRES_JSON, "w", encoding="utf-8") as f:
        json.dump(offers, f, indent=2, ensure_ascii=False)
    print(f"\n✅ {len(offers)} offres sauvegardées dans {OFFRES_JSON}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Scraper offres formation cybersécurité IDF")
    parser.add_argument("--sources", help="Sources à scraper (séparées par des virgules)")
    parser.add_argument("--update", action="store_true", help="Scraper + fusionner avec offres.json")
    args = parser.parse_args()

    print("=" * 60)
    print(f"Cyber-Tech — Scraper Veille Formation Cybersécurité IDF")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)

    # Scraper
    new_offers = extract_with_playwright()

    if not new_offers:
        print("\n⚠️  Aucune nouvelle offre trouvée via le scraping.")

    if args.update:
        existing = load_existing_offers()
        print(f"\n📂 Offres existantes: {len(existing)}")
        merged = merge_offers(existing, new_offers)
        save_offers(merged)
    else:
        save_offers(new_offers if new_offers else [])
        if new_offers:
            print(f"\n📊 Résultats bruts sauvegardés.")