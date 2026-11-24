"""Council of Achrona: Raadsleden debatteren, de Koning leidt het debat en stelt het Verdict op.

Start met `uv run council`. Schrijft verdict.json en trace.json in de root van de repo.

Opbouw:
  - Raadsleden (MODEL_KLEIN) lezen elk alleen hun eigen Kennisbron.
  - Na elke Raadslid-beurt toetst de code de genoemde record-ID's tegen de Kennisbronnen
    (bestaat het ID, en hoort het bij die Rol?). Het resultaat staat in de trace en in het debat,
    zodat de Koning verzonnen ID's ziet. De Koning leest zelf geen Kennisbron.
  - De Koning (MODEL_GROOT) kiest als agent wie spreekt, met welke vraag en waarom, houdt open
    vragen bij en stopt zelf. Daarna stelt hij het Verdict en de geschillen op.
  - Elke prompt blijft onder CONTEXT_BUDGET tokens (standaard 100k): oudere debatbeurten worden
    ingekort als het debat te lang wordt.
"""
import asyncio
import json
import os
import re
import sys
import uuid
from contextlib import AsyncExitStack
from datetime import datetime
from pathlib import Path

import openai
from agent_framework import Agent, MCPStreamableHTTPTool
from agent_framework.openai import OpenAIChatCompletionClient
from dotenv import load_dotenv
from openai import AsyncOpenAI, OpenAI

import raadsleden

ROOT = Path(__file__).parent
KENNISBRONNEN = ROOT / "kennisbronnen"
ROLLEN = ("archmage", "engineer", "guardian_keeper", "historian", "oracle", "beast_master")
PREFIX = {"archmage": "ARC", "engineer": "ENG", "guardian_keeper": "GUA", "historian": "HIS", "oracle": "ORA", "beast_master": "BEA"}
ROL_VAN_PREFIX = {v: k for k, v in PREFIX.items()}
BEURTENBUDGET = 10  # spelregel: maximaal 10 Raadslid-beurten (berichten van Raadsleden) per run
TEKENS_PER_TOKEN = 3  # voorzichtige schatting voor Nederlandse tekst (echte tellingen staan in de trace)
ID_PATROON = re.compile(r"\b(ARC|ENG|GUA|HIS|ORA|BEA)[\-‐‑‒–—―−](\d{3})\b")

# Gedeelde toestand van de run, gezet in run(): kies_volgende() is gewone, niet-async code.
STAAT = {"verbruik": {}, "opties": {}}


# ---------------------------------------------------------------- hulpmiddelen

def context_budget():
    return int(os.getenv("CONTEXT_BUDGET", "100000"))


def schat_tokens(*teksten):
    return sum(len(t) for t in teksten) // TEKENS_PER_TOKEN


def pas_in(regels, vaste_tekst, budget_tokens):
    """Geeft het debat terug als tekst die samen met vaste_tekst binnen het budget past.
    Is het te lang, dan worden de oudste beurten eerst ingekort (de laatste beurten blijven volledig)."""
    regels = list(regels)
    marge = 4000  # ruimte voor het antwoord en de opmaak
    i = 0
    while schat_tokens(vaste_tekst, *regels) > budget_tokens - marge and i < len(regels) - 2:
        if len(regels[i]) > 400:
            regels[i] = regels[i][:400] + " [...ingekort wegens contextbudget]"
        i += 1
    while schat_tokens(vaste_tekst, *regels) > budget_tokens - marge and len(regels) > 2:
        regels.pop(0)
    return "\n\n".join(regels) or "(nog niets)"


def ids_in(tekst):
    """Alle record-ID's in een tekst, met speciale koppeltekens vervangen door een gewoon '-'."""
    return list(dict.fromkeys(f"{p}-{n}" for p, n in ID_PATROON.findall(tekst or "")))


def normaliseer_ids(tekst):
    return ID_PATROON.sub(lambda m: f"{m.group(1)}-{m.group(2)}", tekst or "")


def bron_ids(rol):
    """De record-ID's die echt in de Kennisbron van een Rol staan (alleen om te controleren)."""
    gevonden = set()
    for p in kennisbron_bestanden(rol):
        gevonden.update(i for i in ids_in(p.read_text(encoding="utf-8")) if i.startswith(PREFIX[rol]))
    return gevonden


def controleer_ids(rol, tekst, bekend, eerder_genoemd):
    """Toetst de ID's in een Raadslid-bericht.
    geldig:    eigen ID dat in de eigen Kennisbron staat
    verwijzing: ID van een andere Rol dat eerder in het debat geldig genoemd werd
    onbekend:  eigen ID dat niet in de eigen Kennisbron staat, of een ID van een andere Rol dat nog niemand noemde"""
    uitslag = {"geldig": [], "verwijzing": [], "onbekend": []}
    for i in ids_in(tekst):
        eigen = ROL_VAN_PREFIX[i[:3]] == rol
        if eigen and bekend.get(rol) is None:
            uitslag["geldig"].append(i)  # geen lokale bestanden: niet te controleren
        elif eigen:
            uitslag["geldig" if i in bekend[rol] else "onbekend"].append(i)
        else:
            uitslag["verwijzing" if i in eerder_genoemd else "onbekend"].append(i)
    return uitslag


def lees_json(tekst):
    """Haalt het JSON-object uit een modelantwoord (modellen zetten er soms tekst of ``` omheen)."""
    t = re.sub(r"<think>.*?</think>", "", tekst or "", flags=re.S).strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t).strip()
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        start, eind = t.find("{"), t.rfind("}")
        if start >= 0 and eind > start:
            return json.loads(t[start:eind + 1])
        raise


def tel_openai(model, usage):
    if not usage:
        return
    v = STAAT["verbruik"].setdefault(model, {"beurten": 0, "invoer": 0, "gecached": 0, "uitvoer": 0})
    v["beurten"] += 1
    v["invoer"] += usage.prompt_tokens or 0
    details = getattr(usage, "prompt_tokens_details", None)
    v["gecached"] += (getattr(details, "cached_tokens", 0) or 0) if details else 0
    v["uitvoer"] += usage.completion_tokens or 0


_koning_client = None


def koning_json(systeem, gebruiker):
    """Eén chat-call naar MODEL_GROOT die een JSON-object teruggeeft. Geeft (data, invoertokens)."""
    global _koning_client
    if _koning_client is None:
        _koning_client = OpenAI(base_url=os.environ["OPENAI_BASE_URL"], api_key=os.environ["OPENAI_API_KEY"], max_retries=8)
    berichten = [{"role": "system", "content": systeem}, {"role": "user", "content": gebruiker}]
    extra = dict(STAAT["opties"] or {})
    json_modus = True
    laatste_fout = None
    for _ in range(4):
        try:
            kwargs = {"model": os.environ["MODEL_GROOT"], "messages": berichten, **extra}
            if json_modus:
                kwargs["response_format"] = {"type": "json_object"}
            r = _koning_client.chat.completions.create(**kwargs)
        except openai.BadRequestError as e:
            if json_modus:  # endpoint kent geen JSON-modus: probeer zonder
                json_modus, laatste_fout = False, e
                continue
            raise
        tel_openai("groot", r.usage)
        inhoud = r.choices[0].message.content or ""
        try:
            return lees_json(inhoud), (r.usage.prompt_tokens if r.usage else None)
        except (json.JSONDecodeError, ValueError) as e:
            laatste_fout = e
            berichten += [{"role": "assistant", "content": inhoud},
                          {"role": "user", "content": "Dat was geen geldig JSON-object. Antwoord alleen met het JSON-object."}]
    raise RuntimeError(f"De Koning gaf geen geldige JSON: {laatste_fout}")


# ---------------------------------------------------------------- de Koning leidt het debat

KONING_ROUTERING = """Je bent de Koning van de Council of Achrona en je leidt een onderzoek naar de oorzaak van de Desync.
Je hebt zelf geen Kennisbron: je weet alleen wat de Raadsleden in het debat zeggen. Elke Rol heeft een eigen Belang en kan ernaast zitten; een Raadslid kan ook iets weglaten dat hem slecht uitkomt.

Het doel is een Verdict met drie delen van de oorzaak, elk met record-ID's als bewijs:
- ingreep: wie deed wat, wanneer;
- mechanisme: hoe leidt dat tot de symptomen;
- verloop: welk patroon toont het in de tijd;
plus een veilig, geordend herstelplan, risico's en een voorspelling wanneer het opnieuw gebeurt als niemand ingrijpt.

Er zijn maximaal 10 Raadslid-beurten. Elke beurt telt: laat niemand herhalen wat al gezegd is.

Werkwijze:
1. Zolang niet elke Rol gesproken heeft, geef je het woord aan een Rol die nog niet sprak. Stel een gerichte vraag die aansluit bij wat al gezegd is: vraag naar concrete afwijkingen met dag, tijd en record-ID, naar veranderingen of nieuwe installaties, en naar wie daarvoor toestemming gaf.
2. Daarna toets je, en altijd eerst het ZWAKSTE onderdeel van de stand (ingreep, mechanisme, verloop, herstel). Besteed hoogstens één toetsbeurt aan een detail van een onderdeel dat al sterk is (bv. wie precies toestemming gaf) zolang een ander onderdeel nog zwak is. Een theorie van één Rol is pas sterk als gegevens van een andere Rol ze steunen.
3. Mechanisme: vraag de Rol die verantwoordelijk is voor een getroffen systeem hoe dat systeem volgens zijn eigen regels, voorschriften of specificatie werkt, en of de ingreep daarmee precies dat symptoom kan verklaren, ook het ritme in de tijd.
4. Verloop: zoek het patroon in de tijd. Op welke dagen en uren gebeurt het, met welke regelmaat, en wat veranderde er vlak vóór de eerste keer? Vraag Rollen met metingen op vaste momenten of hun metingen het ritme volgen, en of de dagen tussenin normaal zijn.
   Een vaste regelmaat vraagt om een verklaring. Een bekend patroon: twee dingen die elk in hun eigen, net iets verschillend tempo lopen, lopen langzaam uit de pas en vallen na een vaste periode weer op dezelfde manier samen, zoals twee klokken die niet even snel lopen. Toets zo'n verklaring: vraag de Rol die tempo's, instellingen of afstellingen kent of iets in een ander tempo loopt dan wat er al was, en vraag de Rol met de regels van het getroffen systeem wat er gebeurt als verkeer niet op de verwachte tik binnenkomt. Toets ook of het ritme vóór de ingreep al bestond.
5. Herstel: vraag de Rol die de ingreep uitvoerde welke instellingen er zijn om ze veilig bij te sturen of terug te draaien. Vraag ook of er voorschriften zijn over hoe je herstelt zonder schade, en of een voorgestelde oplossing (bv. iets abrupt uitzetten) zelf schade kan doen.
6. Jij bent degene die de stukken verbindt: elk Raadslid ziet alleen zijn eigen bron. Combineer feiten van verschillende Rollen zelf tot een concrete hypothese (bv. "als X sinds dag N in een ander tempo loopt dan Y, dan ...") en leg die hypothese voor aan de Rol wiens gegevens ze kunnen toetsen. Vraag niet alleen "weet je iets over X?".
7. Elke Rol spreekt hoogstens 3 keer. Laat een Rol niet twee keer na elkaar spreken, tenzij alleen zij het antwoord kan geven.
8. Een regel [CONTROLE: ...] na een bericht noemt ID's die niet in de Kennisbron van dat Raadslid staan. Vertrouw die niet; laat ze zo nodig corrigeren.
9. Stoppen is een bewuste beslissing van jou. Stel jezelf vóór elke keuze de vraag: zou nog een beurt een onderdeel van het Verdict veranderen? Zo niet, stop dan (rol null) en zeg in de reden welke onderdelen sterk staan en waarom een extra beurt niets meer toevoegt. Gebruik beurten niet omdat ze er zijn: zelf stoppen vóór het budget op is, is beter dan doorgaan met herhalingen. Vanaf 8 gebruikte beurten stop je, tenzij één concrete open vraag een onderdeel nog van zwak naar sterk kan brengen. Stop nooit voordat iedere Rol één keer gesproken heeft.

Antwoord ALLEEN met één JSON-object:
{"rol": "<rol-sleutel uit de lijst, of null om te stoppen>",
 "vraag": "<de vraag aan die Rol, hoogstens 60 woorden; null als je stopt>",
 "reden": "<waarom deze Rol nu: concreet, verwijs naar wat er gezegd is of wat ontbreekt>",
 "open_vragen": ["<wat de Council nog niet weet, na deze keuze>"],
 "stand": {"ingreep": "<huidige hypothese of 'onbekend'> [zwak|matig|sterk]", "mechanisme": "... [zwak|matig|sterk]", "verloop": "... [zwak|matig|sterk]", "herstel": "... [zwak|matig|sterk]"}}"""


def debat_regels(beurten, leden):
    """Het debat als tekstregels voor een prompt: vragen van de Koning en antwoorden van de Raadsleden."""
    namen = {l.ROL: l.NAAM for l in leden}
    regels = []
    for b in beurten:
        if b["soort"] == "routering" and b.get("aan"):
            regels.append(f"Koning → {namen.get(b['aan'], b['aan'])}: {b.get('vraag')}")
        elif b["soort"] == "bericht" and b["spreker"] in namen:
            regel = f"{namen[b['spreker']]} ({b['spreker']}): {b['tekst']}"
            onbekend = (b.get("id_controle") or {}).get("onbekend")
            if onbekend:
                regel += f"\n[CONTROLE: {', '.join(onbekend)} bestaat niet in de Kennisbron van {namen[b['spreker']]} of werd nog door niemand geldig genoemd]"
            regels.append(regel)
    return regels


def kies_volgende(beurten, leden):
    """De Koning leidt het debat: hij beslist wie spreekt. De kit roept deze functie op vóór elke beurt.

    Geeft (rol, vraag, reden) of (None, None, reden) terug, plus extra velden voor de routering
    (open_vragen, stand, context_tokens) via kies_volgende.extra.
    """
    per_rol = {l.ROL: l for l in leden}
    gesproken = {}
    for b in beurten:
        if b["soort"] == "bericht" and b["spreker"] in per_rol:
            gesproken[b["spreker"]] = gesproken.get(b["spreker"], 0) + 1
    nog_niet = [l.ROL for l in leden if l.ROL not in gesproken]
    resterend = BEURTENBUDGET - sum(gesproken.values())
    vorige = next((b for b in reversed(beurten) if b["soort"] == "routering"), None)

    ledenlijst = "\n".join(
        f"- {l.ROL}: {l.NAAM}. {l.PERSPECTIEF} (al {gesproken.get(l.ROL, 0)} keer gesproken)" for l in leden)
    vast = (f"Raadsleden:\n{ledenlijst}\n\n"
            f"Nog niet gesproken: {', '.join(nog_niet) or 'iedereen sprak al'}\n"
            f"Resterende Raadslid-beurten: {resterend} van {BEURTENBUDGET}\n"
            f"Jouw open vragen van de vorige beurt: {json.dumps((vorige or {}).get('open_vragen') or [], ensure_ascii=False)}\n\n"
            "Debat tot nu toe:\n\n")
    debat = pas_in(debat_regels(beurten, leden), KONING_ROUTERING + vast, context_budget())
    kies_volgende.extra = {}
    try:
        keuze, tokens = koning_json(KONING_ROUTERING, vast + debat + "\n\nWie spreekt nu, met welke vraag en waarom?")
    except Exception as e:  # het debat mag niet stranden op één mislukte call
        print(f"LET OP: Koning-call mislukt ({e}); noodregel gebruikt.")
        if nog_niet:
            return nog_niet[0], "Welke afwijkingen zie je in je gegevens (dag, tijd, record-ID), en wat veranderde er vlak daarvoor?", \
                f"noodregel: Koning-call mislukt; {per_rol[nog_niet[0]].NAAM} sprak nog niet"
        return None, None, "noodregel: Koning-call mislukt en iedereen sprak al"

    rol = keuze.get("rol")
    if isinstance(rol, str):
        sleutel = rol.strip().lower().replace(" ", "_")
        rol = sleutel if sleutel in per_rol else next((l.ROL for l in leden if l.NAAM.lower() == rol.strip().lower()), None)
        if rol is None and keuze.get("rol") not in (None, "null", ""):
            rol = nog_niet[0] if nog_niet else None
            keuze["reden"] = f"{keuze.get('reden', '')} (gekozen Rol '{keuze.get('rol')}' bestaat niet; regel: volgende Rol die nog niet sprak)".strip()
    else:
        rol = None
    vraag = (keuze.get("vraag") or "").strip() or None
    reden = (keuze.get("reden") or "").strip() or "geen reden opgegeven"

    if rol is None and nog_niet and resterend > 0:  # spelregel van onze Koning: eerst hoort hij iedereen
        rol = nog_niet[0]
        vraag = vraag or "Welke afwijkingen zie je in je gegevens (dag, tijd, record-ID), en bevestigen of weerleggen ze wat de anderen zeiden?"
        reden = f"De Koning wilde stoppen ({reden}), maar {per_rol[rol].NAAM} sprak nog niet: eerst hoort hij elke Rol."
    if rol is not None and gesproken.get(rol, 0) >= 3:  # spelregel van onze Koning: hoogstens 3 beurten per Rol
        alternatief = min((l.ROL for l in leden if l.ROL != rol), key=lambda r: gesproken.get(r, 0))
        reden = f"{reden} (maar {per_rol[rol].NAAM} sprak al 3 keer; regel: de vraag gaat naar {per_rol[alternatief].NAAM}, die het minst sprak)"
        rol = alternatief
    if rol is not None and not vraag:
        vraag = "Wat zeggen jouw gegevens over de open vragen hierboven? Noem dag, tijd en record-ID."

    # Stopregel van onze Koning: na 8 beurten stopt hij als zijn eigen stand nergens nog 'zwak' is.
    labels = stand_labels(keuze.get("stand") if isinstance(keuze.get("stand"), dict) else None)
    gebruikt = BEURTENBUDGET - resterend
    if rol is not None and not nog_niet and gebruikt >= 8 and all(l in ("matig", "sterk") for l in labels.values()):
        overzicht = ", ".join(f"{d} {l}" for d, l in labels.items())
        reden = (f"De Koning stopt na {gebruikt} beurten: zijn stand is nergens nog zwak ({overzicht}), dus nog een beurt "
                 f"verandert het Verdict niet wezenlijk. (Hij overwoog: {reden})")
        rol, vraag = None, None

    kies_volgende.extra = {
        "open_vragen": [str(v) for v in (keuze.get("open_vragen") or [])][:8],
        "stand": keuze.get("stand") if isinstance(keuze.get("stand"), dict) else None,
        "context_tokens": tokens,
    }
    return rol, vraag, reden


kies_volgende.extra = {}

ONDERDELEN = ("ingreep", "mechanisme", "verloop", "herstel")


def stand_labels(stand):
    """Het laatste label (zwak/matig/sterk) dat de Koning per onderdeel gaf, of None als het ontbreekt."""
    labels = {}
    for deel in ONDERDELEN:
        tekst = str((stand or {}).get(deel, "")).lower()
        gevonden = re.findall(r"\b(zwak|matig|sterk)\b", tekst)
        # Een letterlijk overgenomen sjabloon ("[zwak|matig|sterk]") telt niet als oordeel.
        labels[deel] = gevonden[-1] if gevonden and "zwak|matig" not in tekst else None
    return labels


# ---------------------------------------------------------------- de Koning stelt het Verdict op

KONING_VERDICT = """Je bent de Koning van de Council of Achrona. Het debat is voorbij; stel nu het Council Verdict op.
Je hebt geen Kennisbron: gebruik uitsluitend wat de Raadsleden in het debat zeiden.

Regels:
- Gebruik als bewijs alleen record-ID's die Raadsleden in het debat noemden. ID's in een [CONTROLE]-regel zijn ongeldig.
- Neem geen theorie over die door gegevens van een andere Rol weerlegd is, ook niet als risico of als "concurrerende hypothese". Leg zulke meningsverschillen vast als geschil, met de uitkomst en het beslissende bewijs.
- Het mechanisme verklaart hoe de ingreep tot elk symptoom leidt en waarom het in dat ritme gebeurt. Het mag een redenering zijn die feiten van verschillende Rollen combineert (regels, voorschriften of specificaties van hun systemen plus de waargenomen tijden), zolang elke stap een ID uit het debat heeft. Verklaar ook het ritme: als iets sinds de ingreep in een eigen tempo loopt naast wat er al was, lopen die twee langzaam uit de pas en vallen ze na een vaste periode weer op dezelfde manier samen. Steun die redenering op de feiten over tempo, instellingen en de waargenomen dagen. Druk onzekerheid uit met zekerheid, niet door het deel leeg te laten. Alleen als er echt geen dragende feiten zijn, zet je bewering null.
- Noemde een Raadslid een voorgeschreven herstelvolgorde of een instelling om veilig bij te sturen, neem die dan op in het herstelplan.
- Een deel van de oorzaak dat je niet met bewijs kunt dragen, zet je op bewering null met een lege bewijslijst.
- zekerheid (0-1) per deel: hoog alleen als gegevens van meerdere Rollen het steunen.
- Herstelplan: de volgorde is de uitvoeringsvolgorde. Controleer bij elke actie of ze zelf schade kan doen en of er eerst iets anders moet gebeuren; als een Raadslid zo'n voorwaarde noemde, volg die.
- voorspelling: toont het verloop een regelmaat, geef dan de eerstvolgende dag na de laatst gemelde keer, met bewijs. Anders null.
- Schrijf ID's met een gewoon koppelteken, bv. ABC-123.

Antwoord ALLEEN met één JSON-object:
{"samenvatting": "<3-5 zinnen>",
 "oorzaak": {
   "ingreep":    {"bewering": "<wie deed wat, wanneer> of null", "bewijs": ["ID", ...], "zekerheid": 0.0},
   "mechanisme": {"bewering": "<hoe leidt dat tot de symptomen> of null", "bewijs": [...], "zekerheid": 0.0},
   "verloop":    {"bewering": "<patroon in de tijd> of null", "bewijs": [...], "zekerheid": 0.0}},
 "acties": [{"actie": "...", "reden": "...", "bewijs": [...]}],
 "risicos": [{"risico": "...", "mitigatie": "..."}],
 "voorspelling": {"dag": 0, "bewering": "...", "bewijs": [...]} of null,
 "geschillen": [{"onderwerp": "...", "standpunten": {"<rol-sleutel>": "<standpunt>"}, "uitkomst": "<hoe beslecht> of null", "bewijs": [...]}]}"""


def zuiver_bewijs(lijst, toegestaan):
    """Houdt alleen ID's over die in het debat geldig genoemd werden (geen verzonnen ID's in het Verdict)."""
    if not isinstance(lijst, list):
        return []
    return list(dict.fromkeys(i for i in (normaliseer_ids(str(x)).strip() for x in lijst) if i in toegestaan))


def tekst_of(waarde, standaard):
    return normaliseer_ids(str(waarde)).strip() if waarde not in (None, "") else standaard


def maak_verdict(ruw, run_id, toegestaan):
    """Zet het antwoord van de Koning om naar een Verdict dat het schema volgt."""
    verdict = {"run_id": run_id, "samenvatting": tekst_of(ruw.get("samenvatting"), "De Council kwam niet tot een samenvatting."), "oorzaak": {}}
    oorzaak = ruw.get("oorzaak") if isinstance(ruw.get("oorzaak"), dict) else {}
    for slot in ("ingreep", "mechanisme", "verloop"):
        d = oorzaak.get(slot) if isinstance(oorzaak.get(slot), dict) else {}
        bewering = d.get("bewering") if isinstance(d.get("bewering"), str) and d.get("bewering").strip() else None
        bewijs = zuiver_bewijs(d.get("bewijs"), toegestaan)
        uit = {"bewering": normaliseer_ids(bewering) if bewering else None, "bewijs": bewijs}
        if bewering and not bewijs:  # schema: een bewering heeft bewijs nodig
            uit = {"bewering": None, "bewijs": [], "zonder_bewijs": normaliseer_ids(bewering)}
        if isinstance(d.get("zekerheid"), (int, float)):
            uit["zekerheid"] = max(0.0, min(1.0, float(d["zekerheid"])))
        verdict["oorzaak"][slot] = uit

    acties = []
    for a in ruw.get("acties") or []:
        if isinstance(a, dict) and a.get("actie"):
            actie = {"actie": tekst_of(a["actie"], ""), "reden": tekst_of(a.get("reden"), "zie debat")}
            bewijs = zuiver_bewijs(a.get("bewijs"), toegestaan)
            if bewijs:
                actie["bewijs"] = bewijs
            acties.append(actie)
    verdict["acties"] = acties or [{"actie": "Het debat opnieuw voeren met gerichtere vragen", "reden": "De Council kwam niet tot een herstelplan."}]

    risicos = [{"risico": tekst_of(r["risico"], ""), "mitigatie": tekst_of(r.get("mitigatie"), "nog te bepalen")}
               for r in (ruw.get("risicos") or []) if isinstance(r, dict) and r.get("risico")]
    verdict["risicos"] = risicos or [{"risico": "De oorzaak is onvoldoende bewezen", "mitigatie": "Meer bewijs verzamelen vóór ingrijpen"}]

    v = ruw.get("voorspelling")
    if isinstance(v, dict) and v.get("bewering"):
        try:
            dag = int(v.get("dag"))
        except (TypeError, ValueError):
            dag = 0
        if dag >= 1:
            verdict["voorspelling"] = {"dag": dag, "bewering": tekst_of(v["bewering"], ""), "bewijs": zuiver_bewijs(v.get("bewijs"), toegestaan)}

    geschillen = []
    for g in ruw.get("geschillen") or []:
        if not isinstance(g, dict) or not g.get("onderwerp"):
            continue
        standpunten = {k.strip().lower().replace(" ", "_"): tekst_of(s, "") for k, s in (g.get("standpunten") or {}).items()} \
            if isinstance(g.get("standpunten"), dict) else {}
        standpunten = {k: s for k, s in standpunten.items() if k in ROLLEN and s}
        if not standpunten:
            continue
        bewijs = zuiver_bewijs(g.get("bewijs"), toegestaan)
        uitkomst = tekst_of(g.get("uitkomst"), None) if g.get("uitkomst") else None
        if uitkomst and not bewijs:  # schema: een beslecht geschil heeft bewijs nodig
            uitkomst = None
        geschillen.append({"onderwerp": tekst_of(g["onderwerp"], ""), "standpunten": standpunten, "uitkomst": uitkomst, "bewijs": bewijs})
    return verdict, geschillen


# ---------------------------------------------------------------- Raadsleden

def controleer(leden):
    """Duidelijke melding in plaats van een traceback bij de meest voorkomende fouten."""
    mist = [v for v in ("OPENAI_BASE_URL", "OPENAI_API_KEY", "MODEL_KLEIN", "MODEL_GROOT") if not os.getenv(v)]
    if mist:
        sys.exit(f"In .env ontbreekt: {', '.join(mist)}. Kopieer .env.example naar .env en vul het in, of zie 'Vooraf installeren' in de README.")
    for lid in leden:
        if lid.ROL not in ROLLEN:
            sys.exit(f"raadsleden/: ROL = {lid.ROL!r} is ongeldig. Gebruik de mapnaam van de Rol: {', '.join(ROLLEN)}.")
    dubbel = {l.ROL for l in leden if [x.ROL for x in leden].count(l.ROL) > 1}
    if dubbel:
        sys.exit(f"Eén Raadslid per Rol: {', '.join(dubbel)} komt meer dan eens voor in raadsleden/.")


def client(model_env):
    return OpenAIChatCompletionClient(
        model=os.environ[model_env],
        async_client=AsyncOpenAI(
            base_url=os.environ["OPENAI_BASE_URL"],
            api_key=os.environ["OPENAI_API_KEY"],
            max_retries=8,  # bij een rate limit (429) wacht de client en probeert opnieuw
        ),
    )


def kennisbron_bestanden(rol):
    map_ = KENNISBRONNEN / rol
    return sorted(p for p in map_.glob("*") if p.suffix in (".md", ".csv")) if map_.is_dir() else []


def instructies(lid, bestanden, mcp):
    tekst = (
        f"Je bent de {lid.NAAM}, een Raadslid in de Council of Achrona. {lid.PERSPECTIEF}\n"
        "Je debatteert met de andere Raadsleden over de oorzaak van de Desync. De Koning stelt je telkens één vraag.\n\n"
        "Regels:\n"
        "1. Baseer je alleen op je eigen Kennisbron. Noem bij elk feit het record-ID precies zoals het in je Kennisbron staat, "
        "met dag en tijd. Verzin nooit een ID. Gebruik geen ID's van andere Rollen als je eigen bewijs.\n"
        "2. Begin met 'Feiten:' (kort, elk feit met ID), daarna 'Mijn lezing:'. Je Belang kan je lezing kleuren, je feiten niet.\n"
        "3. Beantwoord eerst de vraag van de Koning. Zeg expliciet of jouw gegevens een bewering van een ander Raadslid "
        "bevestigen of tegenspreken, met ID.\n"
        "4. Meld veranderingen, toestemmingen en afspraken uit je Kennisbron die met de vraag te maken hebben, ook als ze jou slecht uitkomen.\n"
        "5. Legt de Koning een hypothese voor, zeg dan of je gegevens ermee verenigbaar zijn en waarom, ook als je ze niet sluitend kunt bewijzen. "
        "Noem de regels, voorschriften of specificaties uit je bron die beschrijven hoe jouw systeem werkt.\n"
        "6. Hoogstens 200 woorden. Weet je iets niet, zeg dat eerlijk.\n"
        "7. Schrijf ID's met een gewoon koppelteken."
    )
    if mcp:
        tekst += "\n\nLees of doorzoek je Kennisbron met je tools voor je spreekt."
    elif bestanden:
        tekst += "\n\nJe Kennisbron:\n\n" + "\n\n".join(f"## {p.name}\n\n{p.read_text(encoding='utf-8')}" for p in bestanden)
    else:
        tekst += "\n\nJe hebt nog geen Kennisbron: zeg dat je niets kan bewijzen."
    return tekst


def tel(verbruik, model, usage):
    if not usage:
        return
    v = verbruik.setdefault(model, {"beurten": 0, "invoer": 0, "gecached": 0, "uitvoer": 0})
    v["beurten"] += 1  # één beurt = één agent-run (met MCP soms meerdere model-requests)
    v["invoer"] += usage.get("input_token_count") or 0
    v["gecached"] += usage.get("cache_read_input_token_count") or 0
    v["uitvoer"] += usage.get("output_token_count") or 0


def toolcalls(response):
    for msg in response.messages:
        for c in msg.contents:
            if c.type == "function_call":
                args = c.arguments
                yield c.name, json.loads(args) if isinstance(args, str) and args else (args or {})


# ---------------------------------------------------------------- het debat

async def run():
    load_dotenv(ROOT / ".env")
    opties = {"reasoning_effort": os.environ["REASONING"]} if os.getenv("REASONING") else None  # minder denkwerk = minder tokens
    run_id = f"{datetime.now().astimezone().isoformat(timespec='seconds')}_{uuid.uuid4().hex[:8]}"
    leden = raadsleden.alle()
    controleer(leden)
    beurten, verbruik = [], {}
    STAAT["verbruik"], STAAT["opties"] = verbruik, opties
    trace = {"run_id": run_id, "status": "bezig", "raadsleden": [l.ROL for l in leden], "beurten": beurten,
             "geschillen": [], "verbruik": verbruik, "context_budget": context_budget()}

    def bewaar(naam, data):
        (ROOT / naam).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def beurt(ronde, spreker, soort, **velden):
        beurten.append({"nr": len(beurten) + 1, "ronde": ronde, "spreker": spreker, "soort": soort, **velden})
        bewaar("trace.json", trace)  # na elke beurt: de viewer (`uv run viewer`) toont het debat live

    klein = client("MODEL_KLEIN")
    # Alleen om ID's te controleren: welke record-ID's staan echt in elke Kennisbron (None = niet lokaal aanwezig).
    bekend = {rol: (bron_ids(rol) or None) for rol in ROLLEN}
    geldig_genoemd = set()  # ID's die Raadsleden in dit debat geldig noemden

    async with AsyncExitStack() as stack:
        agents = []
        for lid in leden:
            mcp_url = os.getenv(f"MCP_{lid.ROL.upper()}", "").strip()
            bestanden = [] if mcp_url else kennisbron_bestanden(lid.ROL)
            tools = []
            if mcp_url:
                try:
                    tools.append(await stack.enter_async_context(MCPStreamableHTTPTool(name=f"kennisbron_{lid.ROL}", url=mcp_url)))
                except Exception as e:
                    sys.exit(f"MCP voor {lid.NAAM} ({mcp_url}) is onbereikbaar: {e}\n"
                             f"Is de server al open (vanaf 10:00)? Klopt het pad /{lid.ROL}/mcp? "
                             f"Of laat MCP_{lid.ROL.upper()} leeg om de bestanden uit kennisbronnen/{lid.ROL}/ te gebruiken.")
            elif not bestanden:
                print(f"LET OP: {lid.NAAM} heeft geen Kennisbron (MCP_{lid.ROL.upper()} is leeg en kennisbronnen/{lid.ROL}/ ook).")
            for p in bestanden:  # fallback zonder MCP: welke bestanden gingen in de prompt
                beurt(0, lid.ROL, "bestand", bestand=f"{lid.ROL}/{p.name}")
            instr = instructies(lid, bestanden, mcp_url)
            if schat_tokens(instr) > context_budget() // 2:
                print(f"LET OP: de Kennisbron van {lid.NAAM} is groot (~{schat_tokens(instr)} tokens).")
            agents.append((lid, mcp_url, instr, Agent(klein, instr, name=lid.ROL, tools=tools)))

        (ROOT / "verdict.json").unlink(missing_ok=True)  # setup gelukt: geen Verdict van een vorige run laten staan
        bewaar("trace.json", trace)
        per_rol = {lid.ROL: (lid, mcp_url, instr, agent) for lid, mcp_url, instr, agent in agents}
        ronde = 1
        while True:
            gesproken = sum(1 for b in beurten if b["soort"] == "bericht" and b["spreker"] in per_rol)
            extra = {}
            if gesproken >= BEURTENBUDGET:
                rol, vraag, reden = None, None, f"Beurtenbudget op ({BEURTENBUDGET} Raadslid-beurten)"
            else:
                trace["aan_het_woord"] = "koning"
                bewaar("trace.json", trace)
                rol, vraag, reden = kies_volgende(beurten, leden)
                extra = {k: v for k, v in (kies_volgende.extra or {}).items() if v is not None}
            if rol is not None and rol not in per_rol:
                sys.exit(f"kies_volgende() koos {rol!r}, maar die Rol zit niet in raadsleden/.")
            if rol is not None:
                ronde = gesproken // len(leden) + 1
            # Elke keuze van de Koning staat in de trace: aan wie, welke vraag en waarom (+ open vragen).
            beurt(ronde, "koning", "routering", aan=rol, vraag=vraag, reden=reden, **extra)
            print(f"\n[Koning] {'stopt' if rol is None else '→ ' + per_rol[rol][0].NAAM}: {reden}")
            if rol is None:
                break
            lid, mcp_url, instr, agent = per_rol[rol]
            # Wie ziet wat? Elk Raadslid ziet het debat (vragen + antwoorden), ingekort als het budget dat vraagt.
            staart = f"\n\nVraag van de Koning aan jou: {vraag}"
            debat = pas_in(debat_regels(beurten[:-1], leden), instr + staart, context_budget())
            prompt = "Debat tot nu toe:\n\n" + debat + staart
            trace["aan_het_woord"] = rol
            bewaar("trace.json", trace)
            r = await agent.run(prompt, options=opties)
            tel(verbruik, "klein", r.usage_details)
            for tool, args in toolcalls(r):
                beurt(ronde, rol, "toolcall", tool=tool, argumenten=args, pad=mcp_url)
            tekst = normaliseer_ids(r.text)
            id_controle = controleer_ids(rol, tekst, bekend, geldig_genoemd)
            geldig_genoemd.update(id_controle["geldig"])
            context_tokens = (r.usage_details or {}).get("input_token_count") or schat_tokens(instr, prompt)
            beurt(ronde, rol, "bericht", tekst=tekst, id_controle=id_controle, context_tokens=context_tokens)
            print(f"\n[ronde {ronde}] {lid.NAAM} (~{context_tokens} tokens context):\n{tekst}")
            if id_controle["onbekend"]:
                print(f"  CONTROLE: onbekende ID's {', '.join(id_controle['onbekend'])}")

    # De Koning heeft geen Rol en geen Kennisbron: hij kent alleen wat de Raadsleden inbrachten.
    trace["aan_het_woord"] = "koning"
    bewaar("trace.json", trace)
    vast = f"Geldig genoemde record-ID's in dit debat: {', '.join(sorted(geldig_genoemd)) or '(geen)'}\n\nDebat:\n\n"
    debat = pas_in(debat_regels(beurten, leden), KONING_VERDICT + vast, context_budget())
    try:
        ruw, _ = koning_json(KONING_VERDICT, vast + debat + "\n\nStel nu het Verdict op.")
    except Exception as e:
        print(f"LET OP: het Verdict kon niet opgesteld worden ({e}).")
        ruw = {}
    verdict, geschillen = maak_verdict(ruw, run_id, geldig_genoemd)
    trace["geschillen"] = geschillen
    beurt(ronde + 1, "koning", "bericht", tekst=verdict["samenvatting"])
    print(f"\n[Koning]:\n{verdict['samenvatting']}")

    trace["status"], trace["aan_het_woord"] = "klaar", None
    bewaar("trace.json", trace)
    bewaar("verdict.json", verdict)

    print(f"\nKlaar: verdict.json en trace.json geschreven (run_id {run_id}).")
    for model, v in verbruik.items():
        print(f"Verbruik {model}: {v['beurten']} beurten, {v['invoer']} tokens in ({v['gecached']} gecached), {v['uitvoer']} tokens uit")
    print("Controleer met: uv run validate  en  uv run check")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    asyncio.run(run())


if __name__ == "__main__":
    main()
