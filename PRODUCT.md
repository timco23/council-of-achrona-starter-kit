# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users
De jury van Hack The Future 2026 (challenge 113, Roboest) tijdens een pitch van 3 minuten, op een groot scherm in de zaal. Ze moeten in één oogopslag zien hoe de Koning het debat leidt, wie spreekt en hoe het Council Verdict ontstaat.

## Product Purpose
De debatviewer van de Council of Achrona: toont `trace.json` en `verdict.json` als een zitting in de raadszaal. Tijdens de pitch draait een echte run live (extra uitdaging "draai de Council live tijdens de pitch") en volgt de zaal het debat: de Koning geeft het woord, het Raadslid antwoordt, tot het Verdict en het feest. Succes: de jury begrijpt zonder uitleg waarom een Council beter werkt dan één agent.

## Operating Context
- Lokaal geserveerd door `uv run viewer` (Python, http://127.0.0.1:8100), leest `trace.json`, `verdict.json` en de renders in `visualisatie/renders/` (Blender, CC0-modellen van KayKit).
- De run schrijft `trace.json` na elke beurt; de viewer pollt elke 1,5 s.
- Gelijktijdig te tonen: de Koning-routeringen (aan wie, vraag, reden, open vragen, stand), berichten van Raadsleden (met broncitaten en controle), en het Verdict (oorzaak in drie delen met zekerheid, voorspelling, herstelplan, risico's).

## Capabilities and Constraints
- Eén HTML-bestand (`viewer.html`) zonder build-stap; `viewer.py` serveert alleen trace/verdict en `.png`/`.json` uit `visualisatie/renders/`.
- Zes Rollen (archmage, engineer, guardian_keeper, historian, oracle, beast_master) plus de Vorstkoning; schermposities van de figuren staan in `posities_zaal.json` en `posities_feest.json`.
- Moet ook bruikbaar blijven tijdens een lopende run (live volgen) en na de run (herhalen).

## Brand Commitments
- Stijl afgestemd op de officiële challengepagina "The Curse of Achrona" van Hack The Future 2026 (gotische blauwe titels, perkament, paarse rook, fantasy met een digitaal randje), met de eigen 3D-renders als hoofdbeeld. Geen logo's of merkmateriaal van Hack The Future, De Cronos Groep of Roboest overnemen.
- Eigen Vorstkoning (ijskroon); geen bestaande game-personages of -stijlen namaken.

## Evidence on Hand
- Renders: `visualisatie/renders/raadszaal.png`, `feest.png`, `avatar_<rol>.png` (CC0 KayKit, zie `visualisatie/CREDITS.md`).
- Echte run-uitvoer: `trace.json`, `verdict.json`.

## Product Principles
- De zitting staat centraal: wie spreekt en wat hij zegt, is altijd het grootste ding op het scherm.
- Elke bewering blijft herleidbaar: ID's, broncitaten en de reden van de Koning blijven zichtbaar.
- Live eerst: een lopende run volgen moet zonder klikken werken.
- Leesbaar van achter in de zaal: grote tekst, hoog contrast.
