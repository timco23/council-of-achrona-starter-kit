"""Council of Achrona: een mini-Council met Raadsleden en een Koning.

Start met `uv run council`. Schrijft verdict.json en trace.json in de root van de repo.
De Koning leidt het debat in `kies_volgende()`: een LLM-agent (MODEL_GROOT) die elke beurt het debat leest
en als JSON teruggeeft wie spreekt, met welke vraag en waarom. Hij beslist zelf wanneer hij stopt.
"""
import asyncio
import json
import os
import sys
import uuid
from contextlib import AsyncExitStack
from datetime import datetime
from pathlib import Path

from agent_framework import Agent, MCPStreamableHTTPTool
from agent_framework.openai import OpenAIChatCompletionClient
from dotenv import load_dotenv
from openai import AsyncOpenAI

import raadsleden

ROOT = Path(__file__).parent
KENNISBRONNEN = ROOT / "kennisbronnen"
ROLLEN = ("archmage", "engineer", "guardian_keeper", "historian", "oracle", "beast_master")
BEURTENBUDGET = 10  # spelregel: maximaal 10 Raadslid-beurten (berichten van Raadsleden) per run


KONING_INSTRUCTIES = """Je bent de Koning van de Council of Achrona en je leidt het debat over de oorzaak van de Desync.
Je hebt geen Kennisbron: je kent alleen wat de Raadsleden in het debat inbrachten.
Vóór elke beurt kies je één Raadslid dat nu spreekt, met één gerichte vraag. Elke beurt is kostbaar.

Een goede keuze:
- vult een gat: welk deel van de oorzaak (ingreep, mechanisme, verloop) is nog onbekend of zonder bewijs (record-ID's)?
- laat een bewering toetsen: noemt iemand een andere Rol, of doet iemand een bewering die een ander kan bevestigen of weerleggen? Geef die Rol het woord.
- geeft wie nog niet sprak een kans als zijn perspectief iets nieuws kan opleveren;
- vermijdt herhaling: niet dezelfde Rol twee keer na elkaar, tenzij die een directe tegenspraak moet uitklaren;
- stelt een concrete vraag die naar het debat verwijst, niet "geef je inbreng".

Stop zelf (rol null) zodra de Council genoeg weet: ingreep, mechanisme en verloop hebben elk een bewering met record-ID's
en de belangrijkste tegenspraak is uitgeklaard, of geen enkel Raadslid kan nog iets nieuws toevoegen.
Stop nooit vóór het eerste bericht.

Antwoord met alleen één JSON-object, zonder tekst eromheen:
{"rol": "<ROL van een Raadslid of null>", "vraag": "<vraag aan dat Raadslid, of null bij stoppen>", "reden": "<waarom deze keuze, concreet: welk gat of welke bewering>"}"""


def koning_prompt(beurten, leden, over):
    raad = "\n".join(f"- {l.ROL}: {l.NAAM}. {l.PERSPECTIEF}" for l in leden)
    namen = {l.ROL: l.NAAM for l in leden}
    regels = []
    for b in beurten:
        if b["soort"] == "routering":
            regels.append(f"[Koning → {b['aan'] or 'stop'}] vraag: {b['vraag']} (reden: {b['reden']})")
        elif b["soort"] == "bericht" and b["spreker"] in namen:
            regels.append(f"{namen[b['spreker']]} ({b['spreker']}): {b['tekst']}")
    gesproken = {b["spreker"] for b in beurten if b["soort"] == "bericht"}
    nog_niet = [l.ROL for l in leden if l.ROL not in gesproken]
    return (
        f"Raadsleden:\n{raad}\n\n"
        "Debat tot nu toe:\n\n" + ("\n\n".join(regels) or "(nog niets)")
        + f"\n\nNog niet gesproken: {', '.join(nog_niet) or 'iedereen sprak al'}."
        + f"\nResterende Raadslid-beurten: {over}."
        + "\n\nWie spreekt nu, met welke vraag en waarom? Of stop je? Antwoord met alleen het JSON-object."
    )


def lees_keuze(tekst, rollen):
    """Haalt {"rol", "vraag", "reden"} uit het antwoord, ook met tekst of ```json eromheen."""
    begin, einde = (tekst or "").find("{"), (tekst or "").rfind("}")
    if begin < 0 or einde < begin:
        raise ValueError("geen JSON-object in het antwoord")
    data = json.loads(tekst[begin:einde + 1])
    rol = data.get("rol")
    if isinstance(rol, str) and rol.strip().lower() in ("", "null", "none", "stop"):
        rol = None
    reden = str(data.get("reden") or "").strip()
    if not reden:
        raise ValueError("geen reden opgegeven")
    if rol is None:
        return None, None, reden
    rol = str(rol).strip().lower()
    if rol not in rollen:
        raise ValueError(f"rol {rol!r} zit niet in de Council; kies uit {', '.join(rollen)} of null")
    vraag = str(data.get("vraag") or "").strip()
    if not vraag:
        raise ValueError("geen vraag opgegeven")
    return rol, vraag, reden


async def kies_volgende(beurten, leden, koning, verbruik, opties=None):
    """De Koning leidt het debat als agent (in AI-termen: een orchestrator). De kit roept dit op vóór elke beurt.

    De Koning (MODEL_GROOT) leest het debat tot nu toe en de Raadsleden, en antwoordt met JSON:
      {"rol": ..., "vraag": ..., "reden": ...}   wie nu spreekt, welke vraag en waarom
      {"rol": null, "vraag": null, "reden": ...}  het debat stopt, met de reden waarom
    Hij beslist zelf wanneer de Council genoeg weet. Het Beurtenbudget bewaakt de kit in run().
    Geeft hij twee keer geen bruikbaar antwoord, dan valt de kit terug op een eenvoudige regel.
    """
    rollen = [l.ROL for l in leden]
    gesproken = sum(1 for b in beurten if b["soort"] == "bericht" and b["spreker"] in rollen)
    prompt = koning_prompt(beurten, leden, BEURTENBUDGET - gesproken)
    fout = None
    for _ in range(2):
        vraag_aan_koning = prompt if fout is None else (
            prompt + f"\n\nJe vorige antwoord was onbruikbaar ({fout}). Antwoord met alleen het JSON-object.")
        r = await koning.run(vraag_aan_koning, options=opties)
        tel(verbruik, "groot", r.usage_details)
        try:
            rol, vraag, reden = lees_keuze(r.text, rollen)
        except (ValueError, json.JSONDecodeError) as e:
            fout = str(e)
            continue
        if rol is None and gesproken == 0:
            fout = "je stopte vóór het eerste bericht"
            continue
        return rol, vraag, reden

    # Noodregel: de Koning gaf geen bruikbare keuze. Wie nog niet sprak, anders wie het langst zweeg.
    print(f"LET OP: de Koning gaf geen bruikbare keuze ({fout}); de kit kiest met een noodregel.")
    laatst = {rol: -1 for rol in rollen}
    for i, b in enumerate(beurten):
        if b["soort"] == "bericht" and b["spreker"] in laatst:
            laatst[b["spreker"]] = i
    rol = min(rollen, key=lambda x: laatst[x])
    return rol, "Wat kan jij met je Kennisbron toevoegen of weerleggen aan wat de anderen zeiden? Hoogstens 150 woorden.", \
        f"noodregel: Koning gaf geen geldige JSON ({fout}); {rol} sprak het langst niet"


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
    key = os.environ["OPENAI_API_KEY"]
    return OpenAIChatCompletionClient(
        model=os.environ[model_env],
        async_client=AsyncOpenAI(
            base_url=os.environ["OPENAI_BASE_URL"],
            api_key=key,
            max_retries=8,  # bij een rate limit (429) wacht de client en probeert opnieuw
        ),
    )


def kennisbron_bestanden(rol):
    map_ = KENNISBRONNEN / rol
    return sorted(p for p in map_.glob("*") if p.suffix in (".md", ".csv")) if map_.is_dir() else []


def instructies(lid, bestanden, mcp):
    tekst = (
        f"Je bent de {lid.NAAM}, een Raadslid in de Council of Achrona. {lid.PERSPECTIEF}\n"
        "Je debatteert met de andere Raadsleden over de oorzaak van de Desync. "
        "Baseer je alleen op je eigen Kennisbron en noem bij elke bewering de record-ID's precies zoals ze in je Kennisbron staan. Verzin nooit een ID. "
        "Zeg het eerlijk als je iets niet weet."
    )
    if mcp:
        tekst += "\nLees of doorzoek je Kennisbron met je tools voor je spreekt."
    elif bestanden:
        tekst += "\n\nJe Kennisbron:\n\n" + "\n\n".join(f"## {p.name}\n\n{p.read_text(encoding='utf-8')}" for p in bestanden)
    else:
        tekst += "\nJe hebt nog geen Kennisbron: zeg dat je niets kan bewijzen."
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


async def run():
    load_dotenv(ROOT / ".env")
    opties = {"reasoning_effort": os.environ["REASONING"]} if os.getenv("REASONING") else None  # minder denkwerk = minder tokens
    run_id = f"{datetime.now().astimezone().isoformat(timespec='seconds')}_{uuid.uuid4().hex[:8]}"
    leden = raadsleden.alle()
    controleer(leden)
    beurten, verbruik = [], {}
    trace = {"run_id": run_id, "status": "bezig", "raadsleden": [l.ROL for l in leden], "beurten": beurten, "geschillen": [], "verbruik": verbruik}

    def bewaar(naam, data):
        (ROOT / naam).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def beurt(ronde, spreker, soort, **velden):
        beurten.append({"nr": len(beurten) + 1, "ronde": ronde, "spreker": spreker, "soort": soort, **velden})
        bewaar("trace.json", trace)  # na elke beurt: de viewer (`uv run viewer`) toont het debat live

    klein = client("MODEL_KLEIN")
    groot = client("MODEL_GROOT")
    voorzitter = Agent(groot, KONING_INSTRUCTIES, name="koning_voorzitter")

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
            agents.append((lid, mcp_url, Agent(klein, instructies(lid, bestanden, mcp_url), name=lid.ROL, tools=tools)))

        (ROOT / "verdict.json").unlink(missing_ok=True)  # setup gelukt: geen Verdict van een vorige run laten staan
        bewaar("trace.json", trace)
        per_rol = {lid.ROL: (lid, mcp_url, agent) for lid, mcp_url, agent in agents}
        debat, ronde = [], 1
        while True:
            gesproken = sum(1 for b in beurten if b["soort"] == "bericht" and b["spreker"] in per_rol)
            if gesproken >= BEURTENBUDGET:
                rol, vraag, reden = None, None, f"Beurtenbudget op ({BEURTENBUDGET} Raadslid-beurten)"
            else:
                rol, vraag, reden = await kies_volgende(beurten, leden, voorzitter, verbruik, opties)
            if rol is not None and rol not in per_rol:
                sys.exit(f"kies_volgende() koos {rol!r}, maar die Rol zit niet in raadsleden/.")
            if rol is not None:
                ronde = gesproken // len(leden) + 1
            # Elke keuze van de Koning staat in de trace: aan wie, welke vraag en waarom.
            beurt(ronde, "koning", "routering", aan=rol, vraag=vraag, reden=reden)
            print(f"\n[Koning] {'stopt' if rol is None else '→ ' + per_rol[rol][0].NAAM}: {reden}")
            if rol is None:
                break
            lid, mcp_url, agent = per_rol[rol]
            # Wie ziet wat? Hier ziet elk Raadslid het hele debat (broadcast). Ook dat is een keuze.
            prompt = "Debat tot nu toe:\n\n" + ("\n\n".join(debat) or "(nog niets)") + f"\n\nVraag aan jou: {vraag}"
            trace["aan_het_woord"] = rol
            bewaar("trace.json", trace)
            r = await agent.run(prompt, options=opties)
            tel(verbruik, "klein", r.usage_details)
            for tool, args in toolcalls(r):
                beurt(ronde, rol, "toolcall", tool=tool, argumenten=args, pad=mcp_url)
            beurt(ronde, rol, "bericht", tekst=r.text)
            debat.append(f"{lid.NAAM}: {r.text}")
            print(f"\n[ronde {ronde}] {lid.NAAM}:\n{r.text}")

    # De Koning heeft geen Rol en geen Kennisbron: hij kent alleen wat de Raadsleden inbrachten.
    trace["aan_het_woord"] = "koning"
    bewaar("trace.json", trace)
    koning = Agent(groot, "Je bent de Koning van de Council of Achrona. Je hebt geen Kennisbron.", name="koning")
    r = await koning.run(
        options=opties,
        messages="Debat:\n\n" + "\n\n".join(debat)
        + "\n\nVat samen: waarover zijn de Raadsleden het eens, waarover niet, en welk bewijs (record-ID's) noemden ze?",
    )
    tel(verbruik, "groot", r.usage_details)
    beurt(ronde + 1, "koning", "bericht", tekst=r.text)
    print(f"\n[Koning]:\n{r.text}")

    # TODO voor jullie team: laat de Council dit Verdict zelf invullen (zie schema/verdict.json).
    verdict = {
        "run_id": run_id,
        "samenvatting": "TODO",
        "oorzaak": {slot: {"bewering": None, "bewijs": []} for slot in ("ingreep", "mechanisme", "verloop")},
        "acties": [{"actie": "TODO", "reden": "TODO"}],
        "risicos": [{"risico": "TODO", "mitigatie": "TODO"}],
    }
    trace["status"], trace["aan_het_woord"] = "klaar", None
    bewaar("trace.json", trace)
    bewaar("verdict.json", verdict)

    print(f"\nKlaar: verdict.json en trace.json geschreven (run_id {run_id}).")
    for model, v in verbruik.items():
        print(f"Verbruik {model}: {v['beurten']} beurten, {v['invoer']} tokens in ({v['gecached']} gecached), {v['uitvoer']} tokens uit")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    asyncio.run(run())


if __name__ == "__main__":
    main()
