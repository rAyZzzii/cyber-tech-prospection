#!/usr/bin/env python3
"""Generate daily report and notify if new offers found."""
import json, os, sys, subprocess
from datetime import datetime

BASE = "/home/hermes/cyber-tech-prospection"
OFFRES = f"{BASE}/data/offres.json"
REPORTS = f"{BASE}/reports/daily"
EMAILS = f"{BASE}/reports/emails"

os.makedirs(REPORTS, exist_ok=True)
os.makedirs(EMAILS, exist_ok=True)

today = datetime.now().strftime("%Y-%m-%d")
prev_file = sorted([f for f in os.listdir(REPORTS) if f.endswith(".json")])

# Load current offers
with open(OFFRES) as f:
    offers = json.load(f)

# Count statuses
total = len(offers)
non_contacte = sum(1 for o in offers if o.get("statut") == "Non contacté")
envoye = sum(1 for o in offers if o.get("statut") == "Email envoyé")
reponse_pos = sum(1 for o in offers if o.get("statut") == "Réponse positive")

report = {
    "date": today,
    "total_offres": total,
    "statuts": {"non_contacte": non_contacte, "envoye": envoye, "reponse_positive": reponse_pos},
    "offres": [
        {
            "titre": o["titre"],
            "etablissement": o["etablissement"],
            "statut": o["statut"],
            "url": o.get("url", ""),
            "source": o.get("source", "")
        }
        for o in offers
    ]
}

# Save report
report_path = f"{REPORTS}/{today}_rapport.json"
with open(report_path, "w") as f:
    json.dump(report, f, indent=2, ensure_ascii=False)

# Generate human-readable summary
summary = f"""
══════════════════════════════════════════
CYBER-TECH PROSPECTION - RAPPORT {today}
══════════════════════════════════════════

Total offres dans la base : {total}
  Non contacté : {non_contacte}
  Email envoyé : {envoye}
  Réponse positive : {reponse_pos}

Offres détaillées :
"""
for o in offers:
    summary += f"\n  [{o['statut']}] {o['titre'][:60]}"
    summary += f"\n         {o['etablissement'][:40]} | {o['localisation'][:25]}"
    if o.get('url'):
        summary += f"\n         {o['url']}"
    summary += ""

summary += f"\n\nRapport sauvegardé : {report_path}"
print(summary)

# Check if any new offers since last report
if prev_file:
    with open(f"{REPORTS}/{prev_file[-1]}") as f:
        prev = json.load(f)
    prev_count = prev.get("total_offres", 0)
    if total > prev_count:
        new_count = total - prev_count
        print(f"\n⚠️  {new_count} NOUVELLE(S) OFFRE(S) DETECTEE(S) !")
        for o in offers:
            # Find the new ones (rough heuristic)
            if o.get("titre") not in [p.get("titre") for p in prev.get("offres", [])]:
                print(f"  ➕ {o['titre'][:60]} - {o['etablissement'][:30]}")
    else:
        print(f"\n✓ Aucune nouvelle offre depuis le dernier rapport")

# Update Excel
subprocess.run([sys.executable, f"{BASE}/scripts/generate_excel.py", "--update"], cwd=BASE)
print("\n✅ Excel mis à jour")