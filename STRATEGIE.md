# Strategie van onze Council

Dit document beschrijft de regels die we sinds de Starter kit hebben toegevoegd, waarom, en wat ze opleverden.
Alle regels zijn **generiek**: prompts en code bevatten geen inhoud uit de Kennisbronnen (geen record-ID's of feiten).
Wat de Council weet, komt uit het debat.

## Uitgangspunt

Bij het lezen van de Kennisbronnen vielen drie dingen op. Elke regel hieronder volgt daaruit:

1. **Het bewijs is verspreid.** Geen enkele Rol kent het hele verhaal. Elk deel van de oorzaak heeft feiten van minstens twee Rollen nodig.
2. **Elke Rol heeft een eigen stokpaardje**, en dat wordt telkens weerlegd door de gegevens van een *andere* Rol.
3. **Niet alles wordt vrijwillig verteld.** Een Rol kan iets verzwijgen dat haar slecht uitkomt.

Daarom werkt een Council hier beter dan één agent: alleen een debat waarin beweringen kruiselings getoetst worden, haalt de oorzaak eruit.

## Architectuur

| Laag | Wat | Model |
|---|---|---|
| Raadsleden | 6 Rollen, elk alleen de eigen Kennisbron (volledig in de prompt) | `MODEL_KLEIN` |
| Broncontrole | Code toetst elk genoemd record-ID tegen de Kennisbron van die Rol | geen LLM |
| Koning: routering | Kiest per beurt Rol, vraag en reden; houdt `open_vragen` en `stand` bij; stopt zelf | `MODEL_GROOT` |
| Koning: Verdict | Concept-Verdict, daarna een review tegen het debat | `MODEL_GROOT` |
| Controle achteraf | `uv run validate` (schema) en `uv run check` (bewijs tegen de bronnen) | geen LLM |

## Regels, redenen en resultaat

### 1. Raadsleden

| Regel | Reden | Resultaat |
|---|---|---|
| Alle 6 Rollen doen mee | Het bewijs is verspreid over alle Rollen | Elk deel van de oorzaak kreeg bewijs van meerdere Rollen |
| Volledige Kennisbron in de prompt in plaats van zoeken via MCP | De bronnen zijn klein (~10 KB); een klein model mist minder als het alles ziet | 0 verzonnen ID's in alle runs |
| Eerst **Feiten** (met ID, dag, tijd), dan **Mijn lezing** | Elke Rol trekt een gekleurde conclusie uit correcte data; zo scheidt de Koning feit van mening | Raadsleden trokken hun eigen stokpaardje zelf in zodra andere data het tegensprak |
| Bevestig of weerspreek expliciet wat anderen zeiden | Maakt kruisverhoor mogelijk | Geschillen worden zichtbaar in het debat |
| Meld veranderingen en toestemmingen, **ook als ze je slecht uitkomen** | Er werd informatie verzwegen | Een verzwegen afspraak kwam in het debat op tafel |
| Reageer op hypotheses van de Koning; noem de regels of specificaties van je eigen systeem | Raadsleden zeiden vaak alleen "staat niet in mijn bron" | Specificaties die het mechanisme dragen, kwamen ter sprake |
| Geef bij vragen over tijd je **hele reeks, ook de normale momenten** | Een ritme bewijs je met het contrast tussen afwijkende en normale momenten | Run 5: normale meetmomenten kwamen in het debat, maar het Verdict gebruikte ze nauwelijks |

### 2. Broncontrole en context (tegen hallucinatie)

| Regel | Reden | Resultaat |
|---|---|---|
| Na elke beurt worden de genoemde ID's getoetst; een ongeldig ID krijgt een `[CONTROLE]`-markering die de Koning ziet | Een verzonnen ID wordt anders door de anderen overgenomen | 0 verzonnen ID's in alle runs |
| In het Verdict komen alleen ID's die een Raadslid in het debat geldig noemde | De Koning leest geen bron en mag dus niets toevoegen | `uv run check` overal groen |
| Contextbudget (`CONTEXT_BUDGET`, standaard 100k): de oudste beurten worden ingekort als het debat te lang wordt | Minder context betekent minder kans op hallucinatie | Grootste context per call ~17k tokens |

### 3. Koning: het debat leiden

| Regel | Reden | Resultaat |
|---|---|---|
| Koning als LLM-agent in plaats van vaste volgorde | Regels zien geen inhoud; een agent leest het debat | Geen enkele routering met "vaste volgorde" |
| Eerst iedereen één keer horen, gericht vragen naar afwijkingen, veranderingen en toestemming | Het bewijs is verspreid | Alle Rollen spraken in elke run |
| **Brede openingsvraag**: in één beurt (a) de volledige reeks inclusief normale momenten, (b) veranderingen en toestemming, (c) de regels van het eigen systeem en hoe je het veilig herstelt | De openingsronde kost 6 van de 10 beurten; in run 6 gingen 2 beurten naar een toestemmingsvraag bij de verkeerde Rol | Run 7: na 6 beurten lag alle kernbewijs op tafel, inclusief de toegegeven toestemming en de volledige meetreeks met normale dagen, telkens in één beurt |
| De toestemmingsvraag **hoogstens één keer per Rol** | De Koning bleef in runs 1 en 6 hangen op die vraag | Run 7: niet meer herhaald; de Koning ging wel achter een ander detail aan (zie conclusie) |
| `open_vragen` en `stand` per onderdeel bijhouden | Extra uitdaging; laat zien wat nog ontbreekt | 10/10 routeringen met open vragen |
| **Het zwakste onderdeel eerst toetsen** (stand zwak/matig/sterk) | In run 1 gingen 3 van de laatste 4 beurten naar één detail | Beurten verdeeld over ingreep, mechanisme, verloop en herstel |
| Gerichte werkwijze voor mechanisme, verloop en herstel | In run 1 kwamen de schildregels en de herstelinstellingen nooit aan bod | Beide kwamen in run 2 en later ter sprake |
| **De Koning vormt zelf hypotheses** over Rollen heen en laat ze toetsen | Elk Raadslid zag alleen zijn stuk; niemand verbond ze (run 2: mechanisme leeg) | Mechanisme ingevuld vanaf run 3 |
| Generiek redeneerpatroon voor een vaste regelmaat: twee tempo's die uit de pas lopen en periodiek samenvallen | Het ritme bleef in run 3 onverklaard | Het ritme werd in run 4 gedeeltelijk verklaard |
| **Zelf stoppen** als een extra beurt het Verdict niet meer verandert, met reden; vangnet in code na 8 beurten als niets meer "zwak" staat | Extra uitdaging; geen beurten verspillen | Run 4: de Koning stopte zelf na 9 beurten |
| Hoogstens 3 beurten per Rol en **nooit twee keer na elkaar**; bij een overtreding kiest de Koning opnieuw | In run 4 kreeg één Rol 3 beurten (2 na elkaar) en een Rol met cruciale metingen er maar 1 | Run 5: geen Rol meer twee keer na elkaar, maar ongelijk verdeeld (3/1/1). Run 6: evenwichtiger, niemand meer dan 2 beurten |

### 4. Koning: het Verdict

| Regel | Reden | Resultaat |
|---|---|---|
| Weerlegde theorieën worden een geschil, niet een risico of "concurrerende hypothese" | In runs 1 en 3 stonden weerlegde theorieën bij de risico's | Opgelost vanaf run 4 |
| Het mechanisme mag een redenering over Rollen heen zijn, zolang elke stap een ID heeft | In run 2 stond het mechanisme op `null` | Ingevuld vanaf run 3 |
| Een voorgeschreven herstelvolgorde uit het debat komt in het herstelplan | Een snelle oplossing kan zelf schade doen | Een veilige volgorde staat in het herstelplan vanaf run 3 |
| Ingreep: wie, wat, wanneer **en wie gaf toestemming** | De verzwegen toestemming is deel van de ingreep | Run 5 en 6: ❌ de toestemming kwam in het debat en in de stopreden van de Koning, maar niet in de ingreep |
| Verloop: waar het patroon optreedt **én waar niet**, met minstens twee onafhankelijke Rollen | In run 4 steunde het verloop op te weinig Rollen | Run 5: ✅ 4 Rollen; ⚠️ de "normale" momenten kwamen van vóór de ingreep. Run 6: ✅ normale nachten tussen de afwijkingen én vóór de ingreep |
| Alleen wat de oorzaak verklaart; een wijziging waarna het patroon onveranderd doorliep, hoort er niet in | In run 4 stond een irrelevante wijziging in de ingreep | Run 5: ✅ die wijziging werd expliciet als "buiten het ritme" benoemd |
| Maximaal 6 acties, elk gericht op oorzaak, symptoom of risico | In run 4 stonden er administratieve nevenzaken tussen | Run 5: ✅ 5 acties, geen nevenzaken; ⚠️ "eerst bewaren" ontbrak. Run 6: ✅ 4 acties, bewaren eerst, daarna stapsgewijs bijsturen |
| **Maatstaf voor zekerheid**: 0.8–1.0 = 3 of meer Rollen, 0.6–0.8 = 2 Rollen, 0.4–0.6 = redenering met een ontbrekende schakel, <0.4 = vermoeden | De zekerheid was willekeurig; een vaste maatstaf maakt ze uitlegbaar | Run 5: ✅ toegepast; de review paste zekerheden aan volgens de maatstaf |
| De **laatste versie** van een bewering telt; een bekentenis tegen het eigen Belang weegt zwaarder dan een eerdere ontkenning; het hele debat telt, ook de laatste beurten | In run 6 kwam een bekentenis uit beurt 8 niet in het Verdict | Run 7: ✅ de toegegeven toestemming staat in de ingreep (2 Rollen) |
| Review: **verzwak geen redenering** die feiten van meerdere Rollen correct combineert (twijfel gaat in `zekerheid`); schrap geen bewijs omdat het laat kwam | In runs 5 en 6 schrapte de review de ritmeverklaring | Run 7: ✅ de ritmeverklaring bleef staan en de review voegde de leylijnen toe als derde Rol voor het verloop; ⚠️ maar ze voegde ook een niet-gemeten "kandidaat" toe aan de ingreep |
| **Review-stap**: de Koning toetst zijn concept aan het debat (7 controles); de correcties staan in de trace als `verdict_review` | Een concept in één keer schrijven laat fouten door | Run 5: ❌ netto negatief (haalde juist bewijs weg, schrapte de ritmeverklaring, las een instelling verkeerd). Run 6: ⚠️ gemengd (voegde terecht normale momenten toe, corrigeerde een ID, zette bewaren eerst, maar schrapte opnieuw de ritmeverklaring). Uit te zetten met `VERDICT_REVIEW=0` |

## Resultaten per run

Alle runs: `uv run validate` en `uv run check` groen, 0 verzonnen record-ID's.

| | Run 1 | Run 2 | Run 3 | Run 4 | Run 5 | Run 6 | Run 7 |
|---|---|---|---|---|---|---|---|
| Nieuw in deze run | Koning-agent, 6 Rollen, broncontrole | zwakste eerst, max. 3 beurten | Koning vormt hypotheses | ritmepatroon, zelf stoppen | verdictregels, review, reeksen, niet twee keer na elkaar | herhaling van run 5 | brede opening, bekentenis telt, review verzwakt niet |
| Raadslid-beurten | 10 | 10 | 10 | 9 | 10 | 9 | 10 |
| Zelf gestopt | nee | nee | nee | **ja** | nee | **ja** | nee |
| Oorzaakdelen ingevuld | 3/3 | 2/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| Rollen achter de ingreep | 1 | 1 | 2 | 2 | 1 | 1 | 2 (+1 ruis) |
| Rollen achter het mechanisme | 2 | — | 3 | 3 | 2 | **4** | 3 |
| Ritme verklaard in het mechanisme | nee | nee | nee | half | nee | nee | **ja** |
| Rollen achter het verloop | 2 | 3 | 4 | 3 | 4 | 3 | **4**, met normale dagen |
| Zekerheid mechanisme / verloop | 0.3 / 0.7 | — / 0.8 | 0.4 / 0.7 | 0.3 / 0.6 | 0.4 / 0.7 | 0.5 / 0.7 | 0.5 / **0.8** |
| Veilige herstelvolgorde in het plan | nee | nee | ja | ja | deels | **ja** | **ja** |
| Geschillen | 6 | 7 | 6 | 9 | 4 | 7 | 7 |
| Grootste context (tokens) | 17.3k | 17.1k | 17.3k | 16.6k | 16.2k | 16.6k | 18.3k |
| Tokens groot model (in / uit) | 72k / 27k | 73k / 26k | 78k / 28k | 81k / 32k | 90k / 39k | 96k / 42k | 139k / 47k |
| Tokens klein model (in / uit) | 127k / 28k | 122k / 33k | 128k / 33k | 111k / 28k | 103k / 34k | 108k / 35k | 136k / 36k |

## Beurtverdeling in run 7

| Beurt | Rol | Doel | Opbrengst |
|---|---|---|---|
| 1–6 | iedereen één keer | brede opening | alle kernbewijs: de ingreep, de toegegeven toestemming, de bouwakte en de tijdstempels, de schildregels, de cyclus bij twee Rollen en de leylijnreeks met normale dagen |
| 7 | Engineer | hypothese toetsen: verschillende tempo's → verkeer tussen tikken → schildregel | ✅ de ritmeverklaring kwam op tafel |
| 8 | Guardian Keeper | een losse melding zonder tijdstip uitzoeken | ⚠️ weinig opbrengst |
| 9 | Historian | precedent en herstelvoorschrift | ⚠️ alleen bevestiging |
| 10 | Engineer | een latere wijziging zonder invloed op het ritme | ❌ een rode haring |

## Conclusie na run 7

- **Het beste Verdict tot nu toe.** Voor het eerst staan alle drie de delen er samen goed in: een ingreep met de toegegeven toestemming, een mechanisme dat ook het ritme verklaart, en een verloop dat steunt op 4 Rollen met normale dagen ertussen (zekerheid 0.8). Het herstelplan begint met bewaren en brengt de polsen langzaam samen.
- **De brede opening werkt.** Na 6 beurten lag al het kernbewijs op tafel; beurt 7 was meteen de beslissende hypothesetoets.
- **Maar de laatste 3 beurten waren grotendeels verspild** en de Koning stopte niet zelf. Hij bleef zijn herstel "zwak" noemen en ging achter details aan (een melding zonder tijdstip, een wijziging zonder invloed). Na beurt 7 had hij kunnen stoppen.
- **Ruis in het Verdict:** de review voegde een niet-gemeten "kandidaat" en een irrelevante wijziging toe aan de ingreep, en een actie over die wijziging.
- **Duurste run:** ~140k tokens in op het grote model (extra calls door het opnieuw kiezen en de review) en ~136k op het kleine model (langere antwoorden). Ruim binnen het budget, maar ongeveer 1,5× run 4.
- **Volgende stap:** de stopregel minder streng maken voor het herstel (een voorschrift plus een instelling uit het debat is "matig"), en in het Verdict: "een kandidaat die niet gemeten is of een wijziging zonder invloed op het ritme hoort niet in de ingreep".

## Conclusie na run 6

- **Run 4 en run 6 zijn de beste**, elk met een eigen sterkte. Run 6 heeft het sterkste mechanisme tot nu toe (4 Rollen: de schildregels, de bouwakte en de afwijkende tijdstempels samen) en het herstelplan begint correct met het bewaren. Run 4 heeft een bredere ingreep (de toegegeven toestemming staat erin) en meer geschillen. Beide stopten zelf.
- **Run 5 was voor een deel pech.** Met dezelfde code gaf run 6 een duidelijk beter Verdict. Eén run per wijziging is dus te weinig om conclusies te trekken.
- **De review-stap is gemengd, niet puur negatief.** In run 6 voegde ze terecht normale momenten toe, schrapte ze een verkeerd gebruikt ID en zette ze het bewaren als eerste actie. Maar in beide runs schrapte ze de ritmeverklaring en hield ze de toegegeven toestemming buiten de ingreep. Ze is dus streng op bewijs, maar te streng voor redeneringen.
- **Twee terugkerende zwaktes:** (1) een toestemming die een Rol in het debat toegaf, komt niet in de ingreep; (2) de ritmeverklaring (twee tempo's die uit de pas lopen) wordt als "onbewezen" geschrapt in plaats van met lage zekerheid opgenomen. Beide zijn op te lossen met een gerichte regel voor de review: "verzwak geen redenering die feiten van meerdere Rollen correct combineert; druk twijfel uit met zekerheid".
- **Kost:** de review voegt per run ongeveer 15k tokens in en 7–10k uit toe op het grote model.

## Wat we bewust niet doen

- **Geen inhoud in prompts of code.** Alle regels gaan over werkwijze, niet over de zaak zelf.
- **De Koning leest geen Kennisbron.** De broncontrole vertelt hem alleen of een ID bestaat, niet wat erin staat.
- **De trace wordt niet bewerkt.** `trace.json` en `verdict.json` komen altijd uit dezelfde run.
