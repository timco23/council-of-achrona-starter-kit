"""Toetst de inhoud van een run tegen de Kennisbronnen. Start met `uv run check`.

`uv run validate` zegt of verdict.json en trace.json geldig zijn. Dit script zegt of ze eerlijk zijn:
  - bestaat elk record-ID in het Verdict echt in de Kennisbron van zijn Rol?
  - werd elk ID in het Verdict door een Raadslid in het debat genoemd (en niet door de Koning verzonnen)?
  - welke ID's verzonnen Raadsleden tijdens het debat?
  - hoe leidde de Koning het debat (redenen, open vragen, zelf gestopt, contextgrootte)?
Het leest de Kennisbronnen alleen om te controleren; het verandert niets aan verdict.json of trace.json.
"""
import json
import sys
from pathlib import Path

from council import BEURTENBUDGET, PREFIX, ROL_VAN_PREFIX, ROLLEN, bron_ids, ids_in

ROOT = Path(__file__).parent


def ids_in_verdict(verdict):
    plekken = []
    for slot, d in (verdict.get("oorzaak") or {}).items():
        plekken += [(f"oorzaak.{slot}", i) for i in d.get("bewijs") or []]
    for n, a in enumerate(verdict.get("acties") or [], 1):
        plekken += [(f"acties[{n}]", i) for i in a.get("bewijs") or []]
    if verdict.get("voorspelling"):
        plekken += [("voorspelling", i) for i in verdict["voorspelling"].get("bewijs") or []]
    return plekken


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    try:
        verdict = json.loads((ROOT / "verdict.json").read_text(encoding="utf-8"))
        trace = json.loads((ROOT / "trace.json").read_text(encoding="utf-8"))
    except FileNotFoundError as e:
        sys.exit(f"Ontbreekt: {e.filename}. Draai eerst `uv run council`.")

    bekend = {rol: bron_ids(rol) for rol in ROLLEN}
    if not any(bekend.values()):
        sys.exit("kennisbronnen/ is leeg: pak pack.zip uit om te kunnen controleren.")
    beurten = trace.get("beurten") or []
    berichten = [b for b in beurten if b.get("soort") == "bericht" and b.get("spreker") in ROLLEN]
    routeringen = [b for b in beurten if b.get("soort") == "routering"]
    in_debat = {}
    for b in berichten:
        for i in ids_in(b.get("tekst")):
            in_debat.setdefault(i, set()).add(b["spreker"])

    fouten, waarschuwingen = [], []

    # 1. Verdict: bestaat elk ID, en werd het in het debat genoemd?
    print("== Verdict ==")
    for plek, i in ids_in_verdict(verdict):
        rol = ROL_VAN_PREFIX.get(i[:3])
        if not rol or i not in bekend.get(rol, set()):
            fouten.append(f"{plek}: {i} bestaat niet in de Kennisbron van {rol or '?'} (verzonnen)")
        elif i not in in_debat:
            fouten.append(f"{plek}: {i} bestaat, maar geen Raadslid noemde het in het debat")
        elif rol not in in_debat[i]:
            waarschuwingen.append(f"{plek}: {i} werd alleen door {', '.join(sorted(in_debat[i]))} genoemd, niet door de {rol} zelf")
    for slot in ("ingreep", "mechanisme", "verloop"):
        d = (verdict.get("oorzaak") or {}).get(slot) or {}
        rollen = sorted({ROL_VAN_PREFIX[i[:3]] for i in d.get("bewijs") or [] if i[:3] in ROL_VAN_PREFIX})
        status = "onbekend (null)" if d.get("bewering") is None else f"{len(d.get('bewijs') or [])} ID's uit {', '.join(rollen)}"
        zeker = f", zekerheid {d['zekerheid']}" if "zekerheid" in d else ""
        print(f"  {slot:11} {status}{zeker}")
        if d.get("bewering") and len(rollen) < 2:
            waarschuwingen.append(f"oorzaak.{slot} steunt op bewijs van maar één Rol")
    print(f"  acties: {len(verdict.get('acties') or [])}, risico's: {len(verdict.get('risicos') or [])}, "
          f"voorspelling: {'dag ' + str(verdict['voorspelling']['dag']) if verdict.get('voorspelling') else 'geen'}, "
          f"geschillen: {len(trace.get('geschillen') or [])}")

    # 2. Debat: verzonnen ID's per Raadslid
    print("\n== Raadsleden ==")
    for rol in trace.get("raadsleden") or []:
        eigen = [b for b in berichten if b["spreker"] == rol]
        genoemd = {i for b in eigen for i in ids_in(b.get("tekst")) if i.startswith(PREFIX[rol])}
        verzonnen = sorted(i for i in genoemd if i not in bekend.get(rol, set()))
        print(f"  {rol:16} {len(eigen)} beurt(en), {len(genoemd)} eigen ID's genoemd, verzonnen: {', '.join(verzonnen) or 'geen'}")
        if verzonnen:
            waarschuwingen.append(f"{rol} noemde ID's die niet in zijn Kennisbron staan: {', '.join(verzonnen)}")
        if not eigen:
            waarschuwingen.append(f"{rol} zit in de Council maar sprak niet")

    # 3. De Koning: routeringen, open vragen, zelf gestopt, context
    print("\n== Koning ==")
    vage = [r for r in routeringen if r.get("reden", "").startswith(("vaste volgorde", "noodregel"))]
    met_vragen = [r for r in routeringen if r.get("open_vragen")]
    stop = next((r for r in routeringen if r.get("aan") is None), None)
    zelf_gestopt = stop and not stop.get("reden", "").startswith("Beurtenbudget op")
    print(f"  routeringen: {len(routeringen)}, met open_vragen: {len(met_vragen)}, vaste volgorde/noodregel: {len(vage)}")
    print(f"  Raadslid-beurten: {len(berichten)} van {BEURTENBUDGET}; zelf gestopt: {'ja' if zelf_gestopt else 'nee'}"
          + (f" ({stop['reden'][:100]})" if stop else ""))
    context = [b["context_tokens"] for b in beurten if isinstance(b.get("context_tokens"), int)]
    budget = trace.get("context_budget", 100000)
    if context:
        print(f"  grootste context: {max(context)} tokens (budget {budget})")
        if max(context) > budget:
            fouten.append(f"een prompt had {max(context)} tokens context, boven het budget van {budget}")
    if vage:
        waarschuwingen.append(f"{len(vage)} routering(en) zonder echte keuze van de Koning")

    print()
    for w in waarschuwingen:
        print("LET OP", w)
    for f in fouten:
        print("FOUT", f)
    print("GROEN: alle ID's in het Verdict bestaan en komen uit het debat." if not fouten else f"ROOD: {len(fouten)} fout(en).")
    sys.exit(1 if fouten else 0)


if __name__ == "__main__":
    main()
