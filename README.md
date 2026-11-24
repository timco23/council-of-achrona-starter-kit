# Council of Achrona: Starter kit

Starter kit voor challenge 113 van Hack The Future 2026, aangeboden door Roboest.

De Desync heeft de herinneringen en systemen van Achrona versnipperd. Jullie bouwen een **Council**: een zwerm van samenwerkende AI-agenten (Raadsleden) die elk één Rol vertolken, debatteren, verspreide kennis analyseren en samen tot een **Council Verdict** komen: wat is de oorzaak, wat is het herstelplan, welke risico's zijn er.

Deze kit geeft jullie binnen het eerste halfuur een draaiende mini-Council die je live in je browser ziet debatteren. Het echte werk is aan jullie: de **Koning** het debat laten leiden. Hij beslist welk Raadslid spreekt, met welke vraag en waarom. (In AI-termen heet dat deel een orchestrator.)

## Wat je krijgt op de dag

| Wat | Wanneer | Waar |
|---|---|---|
| Deze repo (GitHub-template) | vooraf | GitHub |
| LLM-toegang: Teamkaartje met je teamkey voor het Roboest-endpoint ($5 budget, tot 18:00) | 10:00 | coaches |
| Optioneel: je eigen FreeLLMAPI (gratis, zie "FreeLLMAPI (optioneel)") | vooraf | je laptop |
| Rolkaarten: perspectief, Belang en Kennisbron per Rol | in deze repo | `rolkaarten.md` |
| Challenge pack: Kennisbronnen (bestanden) | 10:00 | `https://<mcp-host>/pack.zip` |
| MCP-server: één pad per Rol, `https://<mcp-host>/<rol>/mcp` | antwoordt vanaf 10:00 (daarvoor geeft `uv run council` een MCP-fout) | in je `.env` |
| Coaches | de hele dag | in de zaal |

## Vooraf installeren

- Python 3.12 of hoger
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- git en een GitHub-account
- een code-editor

### LLM-toegang

Op de dag krijgt elk team om 10:00 een **Teamkaartje** met een teamkey voor het Roboest-endpoint (`https://roboest.findingsolutions.be/v1`, OpenAI-compatibel). Je kiest er twee modellen mee: `achrona` (klein, voor de Raadsleden) en `achrona-groot` (voor de Koning). Achter die namen wisselt het endpoint zelf tussen providers. De key heeft een budget van $5 en werkt tot 18:00. Je hoeft vooraf niets te installeren.

### FreeLLMAPI (optioneel)

Wil je een back-up als je budget op is, of zelf modellen kiezen? [FreeLLMAPI](https://github.com/tashfeenahmed/freellmapi) bundelt de gratis tiers van veel LLM-providers achter één OpenAI-compatibel endpoint op je eigen laptop.

1. Installeer het: op Windows de desktop-app uit de [Microsoft Store](https://apps.microsoft.com/detail/9PBN6G8K2B7F); op macOS de app uit [Releases](https://github.com/tashfeenahmed/freellmapi/releases/latest); met Docker `curl -fsSL https://freellmapi.co/install.sh | bash`.
2. Open http://localhost:3001 en voeg op de **Keys**-pagina minstens 2 gratis provider-keys toe (bv. Google AI Studio en Groq). Aanmelden bij een provider vraagt soms een telefoonverificatie: doe dit thuis, niet op de dag.
3. Zet blok 2 van `.env.example` in je `.env` (in plaats van blok 1) met de **unified key** bovenaan de Keys-pagina.

Maak thuis al je repo aan (stap 1–2 hieronder) en draai daarin `uv sync` (en `uv sync --extra devui` als je de DevUI wil). Dan staat alles al geïnstalleerd en verlies je op de dag geen tijd op de wifi.

## Snel starten

1. Klik op **Use this template** en maak een eigen repo aan. Zet die **openbaar**: zo lever je in (zie onderaan).
2. Clone je repo en ga erin staan.
3. Maak je `.env`: kopieer het voorbeeld (`copy .env.example .env` op Windows, `cp .env.example .env` op macOS/Linux), vul in blok 1 de teamkey van je Teamkaartje in en vul de `MCP_<ROL>`-regels in.
4. Open de debatviewer in een tweede terminal:
   ```
   uv run viewer
   ```
5. Start de Council:
   ```
   uv run council
   ```
   In de viewer zie je live wie de Koning aan het woord laat en waarom, wat elk Raadslid zegt, welke Kennisbron het leest en hoeveel tokens het kost.
6. Controleer de uitvoer:
   ```
   uv run validate
   ```
   Groen = `verdict.json` en `trace.json` volgen het schema en komen uit dezelfde run. Groen betekent geldig, nog niet goed: het Verdict van de kit is nog leeg (TODO).

Geen uv? Maak een venv (`python -m venv .venv`, activeer met `.venv\Scripts\activate` op Windows of `source .venv/bin/activate`), dan `pip install -e .` en `python viewer.py`, `python council.py`, `python validate.py`.

Viewer op een andere poort: zet `VIEWER_PORT=8101` als omgevingsvariabele. Een andere map bekijken, bv. het voorbeeld: `uv run viewer voorbeeld`.

## Hoe de kit werkt

```
             ┌────────────── jouw laptop ──────────────┐
             │  council.py ── Koning (leidt, geen bron)│
   (.env) ──►│      │      ── Raadslid (Oracle) ───────┼──► MCP  /oracle/mcp
             │      │      ── Raadslid (Beast Master) ─┼──► MCP  /beast_master/mcp
             │      ▼                                   │
             │  trace.json + verdict.json ──► viewer    │──► LLM via Roboest-endpoint
             └──────────────────────────────────────────┘
```

| Bestand | Wat |
|---|---|
| `council.py` | De Koning die het debat leidt (`kies_volgende()`, een LLM-agent die elke beurt kiest), het debat zelf en het Verdict van de Koning. Schrijft `trace.json` na elke beurt en `verdict.json` aan het einde. |
| `raadsleden/<rol>.py` | Eén bestand per Raadslid: Rol, naam en publiek perspectief. |
| `rolkaarten.md` | De zes Rolkaarten: perspectief, publiek Belang en soort Kennisbron per Rol. Begin hier om je Rollen te kiezen. |
| `viewer.py` + `viewer.html` | De debatviewer (`uv run viewer`). Leest alleen `trace.json` en `verdict.json`, dus werkt ook als je een ander platform kiest. |
| `voorbeelden/devui_debat.py` | Dezelfde Raadsleden als MAF-group chat in de DevUI van Microsoft (zie "Volgende stappen"). |
| `kennisbronnen/` | Leeg (op een LEESMIJ na). Pak `pack.zip` uit in de root van de repo; dan staan de bronnen in `kennisbronnen/<rol>/`. Staat in `.gitignore`. |
| `schema/` | De JSON-schema's van het Council Verdict en de Debat-trace. |
| `voorbeeld/` | Een ingevuld voorbeeld over een verzonnen zaak (een dorpsmolen), om de vorm te zien. Het valideert bewust niet tegen het Achrona-schema. |
| `validate.py` | Toetst je uitvoer aan de schema's. |

## Wat stel je zelf in?

- **Welke Rollen** meedoen: kopieer `raadsleden/oracle.py` naar bv. `raadsleden/engineer.py` en pas aan: `ROL` = de mapnaam van de Rol in kleine letters (`archmage`, `engineer`, `guardian_keeper`, `historian`, `oracle`, `beast_master`); `NAAM` en `PERSPECTIEF` haal je van de Rolkaart in `rolkaarten.md`. Het nieuwe bestand doet vanzelf mee; de volgorde in het debat is alfabetisch op bestandsnaam. Voeg in `.env` een regel `MCP_<ROL>=https://<mcp-host>/<rol>/mcp` toe.
- **Kennisbronnen**: standaard leest elk Raadslid via MCP. Laat je `MCP_<ROL>` leeg, dan plakt de kit de bestanden uit `kennisbronnen/<rol>/` (uit `pack.zip`) in de prompt van dat Raadslid. Heeft een Raadslid geen van beide, dan meldt de kit dat bij de start.
- **Modellen**: `MODEL_KLEIN` voor de Raadsleden, `MODEL_GROOT` voor de Koning, `REASONING` voor het denkwerk. Op het Roboest-endpoint zijn dat `achrona` en `achrona-groot`. Een andere provider kies je alleen via `.env` (blokken voor het Roboest-endpoint, FreeLLMAPI en Ollama). Met FreeLLMAPI kies je `auto:fast`/`auto:smartest` of een vast model uit de catalogus op http://localhost:3001. Support geven we op het Roboest-endpoint en FreeLLMAPI; andere eigen modellen mogen, zonder support.
- **Beurten**: de Koning kiest zelf hoeveel beurten hij gebruikt en stopt wanneer de Council genoeg weet. Het Beurtenbudget (10 Raadslid-beurten) geldt altijd.
- **Het debat zelf**: de instructies, wie wie aan het woord laat (`kies_volgende()`), wat elk Raadslid van het debat ziet, en hoe de Koning het Verdict invult. Dat staat allemaal in `council.py`.

**Verbruik**: je teamkey heeft $5 budget en maximaal 60 calls per minuut; dat volstaat voor tientallen volledige runs. Gratis tiers van FreeLLMAPI hebben eigen limieten per provider. De viewer en de terminal tonen per run hoeveel tokens het kleine en het grote model gebruikten; het staat ook in `trace.json` onder `verbruik`. Bij een rate limit (429) wacht de kit en probeert opnieuw. Budget op? Dan geeft het endpoint een fout over het budget: schakel over op FreeLLMAPI (blok 2) of vraag een coach.

## De Koning leidt het debat

`kies_volgende(beurten, leden, koning, verbruik)` in `council.py` beslist voor elke beurt wie spreekt. De Koning is een agent op `MODEL_GROOT` (instructie: `KONING_INSTRUCTIES`): hij leest het debat tot nu toe (dezelfde `beurten` als in `trace.json`), de Raadsleden en het resterende budget, en antwoordt met JSON `{"rol", "vraag", "reden"}`, of `rol: null` om te stoppen. Onbruikbare JSON krijgt één herkansing; daarna kiest een noodregel wie het langst zweeg. De kit schrijft elke keuze als `routering`-beurt in de trace (`aan`, `vraag`, `reden`) en stopt zelf na 10 Raadslid-beurten.

Standaard is het een vaste volgorde met `reden: "vaste volgorde"`. Laat jullie Koning beter kiezen: als agent (een LLM die het debat leest), met regels in code, of een mix. Vragen om mee te starten: wie moet een bewering toetsen? Welke Rol ontbreekt nog? Wanneer weet je genoeg? Wat moet elk Raadslid van het debat zien?

### Na je eerste run: waar kijk je naar?

Lees het debat in de viewer zoals een jurylid het zou lezen:

- **Routeringen**: staat er overal `vaste volgorde`? Dan kiest jullie Koning nog niets.
- **Toolcalls**: heeft elk Raadslid zijn Kennisbron gelezen vóór het sprak? Een Raadslid zonder toolcall kan feiten en ID's verzinnen, en de anderen nemen dat over.
- **Open sporen**: welke bewering heeft nog niemand getoetst? Waar spreken Raadsleden elkaar tegen? Naar welke andere Rol verwijst iemand?
- **Verspilde beurten**: wie herhaalt of vat alleen samen wat al gezegd is?
- **Oorzaak**: welke delen (ingreep, mechanisme, verloop) zijn nog onbekend?

Wat je daar ziet, verbeter je in `kies_volgende()`.

### Regels of een agent?

Regels in code zijn een goed begin, maar ze zien geen inhoud: ze herkennen hoogstens een naam in een tekst. Twee Raadsleden die over hetzelfde spreken met andere woorden, merkt een regel niet op. Een Koning als **agent** is meestal sneller gebouwd en kiest beter, omdat hij het debat echt leest.

De vorm:

```
Raadsleden + debat tot nu toe  ──►  LLM (MODEL_GROOT)  ──►  {"rol": ..., "vraag": ..., "reden": ...}
```

Wat je daarvoor uitzoekt: een chat-call naar hetzelfde endpoint als de Raadsleden, een instructie die zegt wat een goede keuze is (en wanneer de Koning stopt), en het antwoord als JSON uitlezen. Zoektermen: *structured output*, *JSON mode*, *group chat manager* of *speaker selection* (MAF). Let op: `kies_volgende()` is gewone, niet-async code, en modellen zetten soms tekst rond hun JSON.

## Spelregels

- Eén Raadslid per Rol. Elk Raadslid leest alleen de Kennisbron van zijn eigen Rol. De viewer en de jury kijken dat na in de trace.
- De Koning leidt het debat en stelt het Verdict op, maar leest zelf geen Kennisbron.
- Maximaal 10 Raadslid-beurten per run (het **Beurtenbudget**). Alleen berichten van Raadsleden tellen; toolcalls, Routeringen en berichten van de Koning niet.
- Vóór elke Raadslid-beurt staat een `routering` in de trace: aan wie, welke vraag en waarom. `spreker` is `koning` (in code of als agent), een Rol (handoff) of `mens`.
- Prompts en code bevatten geen inhoud uit de Kennisbronnen (geen record-ID's of feiten). Wat de Council weet, komt uit het debat.
- Menselijke tussenkomst mag, maar staat in de trace als `spreker: "mens"`. Een Routering door een mens telt niet mee voor de Council-score.
- `trace.json` is de ongewijzigde uitvoer van de run die het Verdict maakte. Niet achteraf bewerken.
- Elke Rol heeft een Belang en kan ernaast zitten.

## Wat moet je zelf bouwen?

- Een **Koning** die het debat leidt in plaats van de vaste volgorde, met een reden bij elke keuze.
- Meer Raadsleden (minstens 3 Rollen). Meer Rollen geven meer kennis, maar elke beurt telt. De Kennisbronnen verwijzen soms naar andere Rollen: dat zegt je welke Rol je nog mist.
- Een Koning die het `verdict.json` echt invult: de oorzaak in drie delen (`ingreep`, `mechanisme`, `verloop`), elk met een bewering en record-ID's als bewijs, een geordend herstelplan (`acties`) en minstens één risico. Weet je een deel niet, laat dan `bewering: null`.
- `geschillen` in de trace: waarover waren de Raadsleden het oneens, en hoe werd het beslecht?
- Let op: modellen schrijven ID's soms met een speciaal koppelteken (`ORA‑101`). `uv run validate` meldt dat; vervang het door een gewoon `-`.

## Jurering

Drie criteria, elk 0–10: **Verdict** (40%), **Council** (40%: hoe goed orchestreert jullie Council, zichtbaar in de Routeringen van de trace) en **Presentatie** (20%, met de vraag: waarom werkt jullie Council hier beter dan één agent?). Zonder Extra uitdaging haal je per criterium hoogstens 8 op 10. Voor wie sneller klaar is:

- **Verdict**: voorspel wanneer de Desync opnieuw toeslaat als niemand ingrijpt (optioneel veld `voorspelling {dag, bewering, bewijs[]}`) · geef je zekerheid per deel van de oorzaak (optioneel veld `zekerheid`, 0–1, per slot).
- **Council**: laat je Koning zelf beslissen wanneer het debat klaar is, en waarom (een `routering` met `aan: null` vóór het budget op is) · laat je Koning een lijst open vragen bijhouden en na elke beurt bijwerken (optioneel veld `open_vragen` in de `routering`).
- **Presentatie**: draai de Council live tijdens de pitch · bouw een eigen, rijkere visualisatie van het debat (bovenop of in plaats van de viewer) of geef de Rollen avatars.

## Volgende stappen

- **DevUI**: `uv run --extra devui python voorbeelden/devui_debat.py` opent de DevUI van [Microsoft Agent Framework](https://github.com/microsoft/agent-framework) met dezelfde Raadsleden als group chat. Het gebruikt de bestanden uit `kennisbronnen/<rol>/` (geen MCP: pak eerst `pack.zip` uit) en schrijft geen trace. Handig om orchestratie te verkennen.
- MAF heeft patronen voor orchestratie: een group chat met een manager die de spreker kiest, Handoff (een agent geeft het woord door) en Magentic (een manager met een plan en open vragen). Gebruik ze, of kies een eigen platform: zolang je `verdict.json` en `trace.json` in dit formaat oplevert, met een `routering` vóór elke Raadslid-beurt, mag alles.
- Bouw RAG op de Kennisbronnen: het Roboest-endpoint biedt geen embeddings aan, FreeLLMAPI wel (`/v1/embeddings`).

## Inleveren (om 16:00)

- Je repo is **openbaar** en je deelt de link met ons via het inleverformulier (link bij de briefing).
- Commit en push `verdict.json` en `trace.json` (in de root, uit dezelfde run) vóór 16:00. Alleen de laatste commit vóór 16:00 telt.
- Kleine correcties aan `verdict.json` (bv. koppeltekens) mogen; `trace.json` laat je ongewijzigd.

## Licentie

MIT, zie `LICENSE`.
