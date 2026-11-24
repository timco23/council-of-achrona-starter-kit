"""Eindcontrole van een run, bovenop `uv run validate`. Start met `uv run audit`.

Controleert de spelregels en de herkomst van het bewijs in trace.json en verdict.json:
- schema's en spelregels (via validate.py), zelfde run, run afgerond;
- minstens 3 Rollen spraken; elk Raadslid las zijn eigen bron (eigen MCP-pad) vóór het sprak;
- de Koning las geen Kennisbron;
- elk record-ID in het debat en in het Verdict bestaat echt (als kennisbronnen/ uit pack.zip er staat);
- broncitaten staan letterlijk in het record;
- het Verdict gebruikt alleen ID's die door hun eigen Rol bevestigd werden.
Daarnaast waarschuwingen voor inhoudelijke verbeterpunten (onbekende delen, geen geschillen, ...).
Idee voor een aparte eindcontrole: SamuelMarquezCastro/Hackthefuture (audit.py); eigen uitwerking.
"""
import sys
from pathlib import Path

import validate
from council import PREFIX, ids_in, ruwe_records, vergelijkbaar

ROOT = Path(__file__).parent


def controleer(root=ROOT):
    fouten, waarschuwingen = [], []
    trace, f1 = validate.fouten("trace.json")
    verdict, f2 = validate.fouten("verdict.json")
    fouten += f1 + f2
    if not trace or not verdict:
        return fouten, waarschuwingen
    fouten += validate.spelregels(trace)
    if trace.get("run_id") != verdict.get("run_id"):
        fouten.append("trace.json en verdict.json komen niet uit dezelfde run (run_id verschilt).")
    if trace.get("status") != "klaar":
        fouten.append(f"De run is niet afgerond (status {trace.get('status')!r}).")

    rollen = set(trace.get("raadsleden") or [])
    beurten = trace.get("beurten") or []
    berichten = [b for b in beurten if b["soort"] == "bericht" and b["spreker"] in rollen]
    if len({b["spreker"] for b in berichten}) < 3:
        fouten.append("Minder dan 3 verschillende Rollen spraken (spelregel: minstens 3 Rollen).")

    # Bronlezing: alleen de eigen bron, en vóór elk bericht.
    laatste_routering = None
    gelezen = set()
    for b in beurten:
        if b["soort"] == "routering":
            laatste_routering, gelezen = b, set()
        elif b["soort"] in ("toolcall", "bestand"):
            if b["spreker"] == "koning":
                fouten.append(f"Beurt {b['nr']}: de Koning las een Kennisbron.")
                continue
            pad = b.get("pad") or b.get("bestand") or ""
            if f"/{b['spreker']}/" not in f"/{pad}" and not pad.startswith(f"{b['spreker']}/"):
                fouten.append(f"Beurt {b['nr']}: {b['spreker']} gebruikt een bron die niet van zijn Rol is ({pad}).")
            gelezen.add(b["spreker"])
        elif b in berichten and laatste_routering is not None and b["spreker"] not in gelezen:
            waarschuwingen.append(f"Beurt {b['nr']}: {b['spreker']} sprak zonder bronlezing in deze beurt.")

    # Bestaan de ID's? (alleen als het pack lokaal staat)
    echt, kb = set(), root / "kennisbronnen"
    for p in kb.glob("*/*"):
        if p.suffix in (".md", ".csv"):
            echt |= ids_in(p.read_text(encoding="utf-8"))
    ruw = {}
    for rol in rollen:
        tekst = "\n".join(p.read_text(encoding="utf-8") for p in sorted((kb / rol).glob("*")) if p.suffix in (".md", ".csv"))
        ruw.update(ruwe_records(tekst))
    if not echt:
        waarschuwingen.append("kennisbronnen/ ontbreekt (pak pack.zip uit): het bestaan van ID's is niet gecontroleerd.")

    bevestigd = set()
    for b in berichten:
        bevestigd |= {i for i in b.get("bevestigde_ids", ids_in(b["tekst"])) if i.startswith(PREFIX[b["spreker"]])}
        if echt:
            nep = sorted(ids_in(b["tekst"]) - echt)
            if nep:
                fouten.append(f"Beurt {b['nr']} ({b['spreker']}): ID's die niet bestaan: {', '.join(nep)}")
        for i, citaat in ((b.get("controle") or {}).get("broncitaten") or {}).items():
            if ruw and vergelijkbaar(citaat) not in vergelijkbaar(ruw.get(i, "")):
                fouten.append(f"Beurt {b['nr']}: broncitaat bij {i} staat niet letterlijk in het record.")

    gebruikt = set()
    for d in verdict["oorzaak"].values():
        gebruikt |= set(d.get("bewijs") or [])
    for a in verdict.get("acties") or []:
        gebruikt |= set(a.get("bewijs") or [])
    gebruikt |= set((verdict.get("voorspelling") or {}).get("bewijs") or [])
    if echt and gebruikt - echt:
        fouten.append(f"Verdict noemt ID's die niet bestaan: {', '.join(sorted(gebruikt - echt))}")
    if gebruikt - bevestigd:
        waarschuwingen.append(f"Verdict noemt ID's die geen Raadslid uit zijn eigen bron bevestigde: {', '.join(sorted(gebruikt - bevestigd))}")

    # Inhoudelijke verbeterpunten
    for slot, d in verdict["oorzaak"].items():
        if d.get("bewering") is None:
            waarschuwingen.append(f"Oorzaakdeel {slot} is onbekend (bewering null).")
        elif len({i[:3] for i in d.get("bewijs") or []}) < 2:  # uit hoeveel Kennisbronnen komt het bewijs?
            waarschuwingen.append(f"Oorzaakdeel {slot} rust op één Rol.")
    if not trace.get("geschillen"):
        waarschuwingen.append("Geen geschillen vastgelegd.")
    rout = [b for b in beurten if b["soort"] == "routering"]
    if rout and rout[-1].get("aan") is None and len(berichten) >= validate.BEURTENBUDGET:
        waarschuwingen.append("De Koning stopte niet zelf vóór het Beurtenbudget (extra uitdaging).")
    if not verdict.get("voorspelling"):
        waarschuwingen.append("Geen voorspelling in het Verdict (extra uitdaging).")
    return fouten, waarschuwingen


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    fouten, waarschuwingen = controleer()
    for f in fouten:
        print("FOUT:", f)
    for w in waarschuwingen:
        print("LET OP:", w)
    print("AUDIT:", "GROEN" if not fouten else f"ROOD ({len(fouten)} fout(en))")
    sys.exit(bool(fouten))


if __name__ == "__main__":
    main()
