# Council of Achrona: Challenge pack

Hack The Future 2026 · challenge 113 · Roboest

## De opdracht

De Desync heeft de herinneringen en systemen van Achrona versnipperd. Magie hapert, data lekt, en niemand weet nog precies wat er gebeurd is. Zes figuren van Achrona weten elk een stuk van het verhaal. Geen van hen kent het hele verhaal, en elk van hen heeft een Belang en kan ernaast zitten.

Bouw een **Council**: een zwerm van samenwerkende AI-agenten. Elk Raadslid vertolkt één Rol, leest alleen de eigen Kennisbron, brengt bewijs in en debatteert met de anderen. Samen komen ze tot een **Council Verdict**: wat is de oorzaak van de Desync (wat gebeurde er, hoe leidt dat tot de symptomen, wat toont het patroon in de tijd), wat is het herstelplan, en welke risico's zijn er?

## Wat zit in dit pack

Pak `pack.zip` uit in de root van je repo: je krijgt `LEESMIJ.md`, `rolkaarten.md` en `kennisbronnen/<rol>/`, precies waar de Starter kit de bestanden zoekt als je zonder MCP werkt. (De Starter kit zet `kennisbronnen/*/` in `.gitignore`: commit de bronnen niet in je openbare repo.)

| Map of bestand | Inhoud |
|---|---|
| `rolkaarten.md` | De zes Rolkaarten: perspectief, publiek Belang en soort Kennisbron per Rol. |
| `kennisbronnen/<rol>/` | De Kennisbron van elke Rol: tekst (`.md`) en soms een tabel (`.csv`). Elk record heeft een ID, bv. `ARC-103` of `[ORA-104]`. Gebruik die ID's als bewijs. |

Dezelfde Kennisbronnen zijn ook via MCP beschikbaar: `https://<mcp-host>/<rol>/mcp`, met de tools `lees_kennisbron`, `zoek`, `zoek_betekenis` en `toon`.

## Spelregels

- Minstens 3 Rollen. Eén Raadslid per Rol.
- Elk Raadslid leest alleen de Kennisbron van zijn eigen Rol. Dat moet blijken uit de Debat-trace.
- Een Koning mag het debat leiden en het Verdict opstellen, maar leest zelf geen Kennisbron.
- Jullie **Koning** beslist wie spreekt: vóór elke Raadslid-beurt staat in de trace een `routering` met aan wie, welke vraag en waarom.
- Maximaal 10 Raadslid-beurten per run (het Beurtenbudget).
- Prompts en code bevatten geen inhoud uit de Kennisbronnen (geen record-ID's of feiten). Wat de Council weet, komt uit het debat.
- Menselijke tussenkomst mag, maar staat in de trace als `mens`. Een Routering door een mens telt niet mee voor de Council-score.
- Lever om 16:00 je openbare repo in met `verdict.json` en `trace.json` in de root, uit dezelfde run.

## Tips

- De Rolkaart vertelt wat voor kennis een Rol heeft. De Kennisbronnen verwijzen soms naar een andere Rol: dat zegt je wie je nog mist.
- Een bewering zonder record-ID levert niets op. Weet je iets niet, zeg dat dan eerlijk (`bewering: null`).
- Niet elke conclusie in een Kennisbron klopt. Laat je Raadsleden elkaar tegenspreken.
