#!/usr/bin/env python3
"""
Cyber-Tech Prospection — Scraper unifié des offres de formation cybersécurité IDF

Stratégie:
1. Google Jobs (indexe Indeed, LinkedIn, WTTJ, etc.)
2. Sites carrières des écoles (EPITA, IONIS, etc.)
3. Indeed direct XML/simple

Produit: data/offres.json (fusion avec existant)
"""

import json, os, re, time, sys
from datetime import datetime
from urllib.request import Request, urlopen
from urllib.parse import quote

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
OFFRES_JSON = os.path.join(DATA_DIR, "offres.json")

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"


def fetch(url, timeout=15):
    """Fetch a URL with headers."""
    req = Request(url, headers={"User-Agent": UA, "Accept-Language": "fr-FR,fr;q=0.9"})
    try:
        with urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        return None


def scrape_google_jobs(query, max_results=20):
    """Scrape Google Jobs via SERP."""
    results = []
    encoded = quote(f"{query} Île-de-France emploi 2026")
    url = f"https://www.google.com/search?q={encoded}&ibp=htl;jobs&hl=fr"
    
    html = fetch(url, timeout=15)
    if not html:
        return results

    # Google Jobs JSON-LD
    import json as j
    matches = re.findall(
        r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>',
        html, re.DOTALL
    )
    for m in matches:
        try:
            data = j.loads(m)
            if isinstance(data, dict) and data.get("@type") == "ItemList":
                for item in data.get("itemListElement", []):
                    job = item.get("item", {})
                    title = job.get("title", "")
                    if not title:
                        continue
                    # Filter: must contain cyber/sécurité/security keywords
                    keywords = ["cyber", "sécurité", "security", "réseau", "pentest", "SOC", "hack"]
                    if not any(k in title.lower() for k in keywords):
                        continue
                    
                    results.append({
                        "titre": title,
                        "etablissement": job.get("hiringOrganization", {}).get("name", ""),
                        "type_mission": "Non précisé",
                        "matieres": "Cybersécurité",
                        "niveau": "Non précisé",
                        "localisation": job.get("jobLocation", {}).get("address", {}).get("addressLocality", "Île-de-France"),
                        "date_publication": job.get("datePosted", ""),
                        "date_limite": "",
                        "url": job.get("directApply", "") or job.get("url", ""),
                        "email_contact": "",
                        "statut": "Non contacté",
                        "source": "google_jobs",
                        "notes": f"Trouvé via Google Jobs: {query}"
                    })
        except:
            pass

    return results


def scrape_school_career_pages():
    """Scrape les pages carrières des écoles directement."""
    results = []

    # ── IONIS Group (EPITA, IPSA, etc.) ──
    html = fetch("https://www.epita.fr/recrutement/", timeout=15)
    if html:
        match = re.search(r"window\.allOffers\s*=\s*(\[[\s\S]*?\]);", html)
        if match:
            import json as j
            offers = j.loads(match.group(1))
            for o in offers:
                title = o.get("Title", {}).get("fr-fr", "")
                title_lower = title.lower()
                keywords = ["cyber", "sécurité", "security", "hack", "pentest", "SOC", "réseau", "réseaux"]
                if any(k in title_lower for k in keywords):
                    results.append({
                        "titre": title,
                        "etablissement": f'{o.get("Subsidiary_Name", "IPSA")} — IONIS Group',
                        "type_mission": o.get("TypeTranslated", "CDI"),
                        "matieres": "Réseaux, cybersécurité",
                        "niveau": "Bac+5 (Enseignant)",
                        "localisation": f'{o.get("Address_City", "")} ({o.get("Address_Department", "")}) — Île-de-France',
                        "date_publication": o.get("PublicationStartDate", "")[:10] if o.get("PublicationStartDate") else "",
                        "date_limite": "",
                        "url": o.get("Url", ""),
                        "email_contact": "",
                        "statut": "Non contacté",
                        "source": "school_career",
                        "notes": f'Poste chez {o.get("Subsidiary_Name", "?")} du groupe IONIS. Type: {o.get("TypeTranslated", "CDI")}'
                    })

    # ── ESIEA ──
    html = fetch("https://www.esiea.fr/recrutement/", timeout=15)
    if html:
        # Check if there's a similar JSON structure
        match = re.search(r"window\.__INITIAL_STATE__\s*=\s*(\{[\s\S]*?\});", html)
        if match:
            pass  # ESIEA structure unknown, skip parse

    return results


def scrape_indeed_simple():
    """Scrape Indeed via their simple/XML format."""
    results = []
    queries = [
        "formateur cybersécurité",
        "intervenant vacataire sécurité",
        "chargé de cours cybersécurité",
    ]
    for q in queries:
        encoded = quote(q)
        url = f"https://fr.indeed.com/jobs?q={encoded}&l=Paris+%2875%29&sort=date"
        html = fetch(url, timeout=15)
        if not html:
            continue

        # Indeed has job data in script tags
        import json as j
        # Try extracting from JSON-LD
        matches = re.findall(
            r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>',
            html, re.DOTALL
        )
        for m in matches:
            try:
                data = j.loads(m)
                if isinstance(data, dict) and data.get("@type") == "ItemList":
                    for item in data.get("itemListElement", []):
                        job = item if isinstance(item, dict) else item.get("item", {})
                        if isinstance(job, str):
                            continue
                        title = job.get("title", "") or job.get("name", "")
                        if not title:
                            continue
                        keywords = ["cyber", "sécurité", "security", "réseau", "pentest", "SOC"]
                        if not any(k in title.lower() for k in keywords):
                            continue
                        results.append({
                            "titre": title,
                            "etablissement": job.get("hiringOrganization", {}).get("name", ""),
                            "type_mission": "Non précisé",
                            "matieres": "Cybersécurité",
                            "niveau": "Non précisé",
                            "localisation": job.get("jobLocation", {}).get("address", {}).get("addressLocality", "Paris"),
                            "date_publication": job.get("datePosted", "")[:10] if job.get("datePosted") else "",
                            "date_limite": "",
                            "url": job.get("url", ""),
                            "email_contact": "",
                            "statut": "Non contacté",
                            "source": "indeed",
                            "notes": f"Trouvé via Indeed: {q}"
                        })
            except:
                continue

    return results


def load_existing():
    if os.path.exists(OFFRES_JSON):
        with open(OFFRES_JSON, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def merge_and_save(existing, new):
    existing_urls = {o.get("url", "") for o in existing if o.get("url")}
    merged = list(existing)
    for offer in new:
        url = offer.get("url", "")
        if url and url not in existing_urls:
            merged.append(offer)
            existing_urls.add(url)
            print(f"  ➕ Nouvelle: {offer['titre'][:60]}")
        elif not url:
            # Offers without URL get added if title is unique
            titles = {o.get("titre", "") for o in existing}
            if offer.get("titre", "") not in titles:
                merged.append(offer)
                print(f"  ➕ Nouvelle (sans URL): {offer['titre'][:60]}")
            else:
                print(f"  ⏩ Déjà existante: {offer['titre'][:60]}")
        else:
            print(f"  ⏩ Déjà existante: {offer['titre'][:60]}")

    with open(OFFRES_JSON, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)
    return merged


if __name__ == "__main__":
    print("=" * 60)
    print(f"Cyber-Tech — Scraper Veille Formation Cybersécurité IDF")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)

    existing = load_existing()
    print(f"\n📂 Offres existantes: {len(existing)}")

    all_new = []

    # School career pages (most reliable)
    print("\n🏫 Scraping écoles...")
    school_offers = scrape_school_career_pages()
    if school_offers:
        print(f"  ✅ {len(school_offers)} offres écoles trouvées")
        all_new.extend(school_offers)
    else:
        print("  ⚠️  Aucune offre école")

    # Google Jobs
    print("\n🔍 Scraping Google Jobs...")
    google_keywords = [
        "formateur cybersécurité emploi",
        "enseignant vacataire cybersécurité",
        "formateur SOC Paris",
    ]
    for kw in google_keywords:
        offers = scrape_google_jobs(kw)
        if offers:
            print(f"  ✅ {len(offers)} offres pour '{kw[:40]}'")
            all_new.extend(offers)

    # Indeed
    print("\n🔍 Scraping Indeed...")
    indeed_offers = scrape_indeed_simple()
    if indeed_offers:
        print(f"  ✅ {len(indeed_offers)} offres Indeed")
        all_new.extend(indeed_offers)
    else:
        print("  ⚠️  Aucune offre Indeed (blocage probable)")

    # Merge
    print(f"\n📊 Total nouvelles offres: {len(all_new)}")
    merged = merge_and_save(existing, all_new)
    print(f"\n✅ {len(merged)} offres dans offres.json")

    # Update Excel
    os.system(f"cd {BASE_DIR} && python3 scripts/generate_excel.py --update 2>&1")