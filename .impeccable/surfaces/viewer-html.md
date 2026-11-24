---
version: 1
slug: "viewer-html"
primary_target: "viewer.html"
related_targets: []
---

# Surface brief: viewer.html (Raadszaal van Achrona)

Mode: Experience. The jury watches the Council work; the 3D hall is the work and leads from the first viewport.
Audience and job: Hack The Future jury on a big screen during a 3-minute pitch; follow a live run without clicking.
Proof/content: real trace.json and verdict.json, Blender renders in visualisatie/renders (CC0 KayKit), screen positions in posities_zaal.json / posities_feest.json.
Constraints: one HTML file, served by viewer.py; Dutch; logboek with all run details stays reachable; no HTF/Cronos/Roboest logos or Adobe-kit fonts.
Build path: code-led (no image generation in this harness).

## Direction contract

THESIS: The debate is staged inside the rendered raadszaal: the hall is the screen, speakers talk from their seats in parchment speech scrolls, and the Verdict ends in the feast. It refuses the dashboard-with-chat-log arrangement.

OWN-WORLD: Hack The Future 2026 "Curse of Achrona" world: night-plum ground #160f1f, light-blue gothic display (#e1e7ff) with a soft dark drop shadow, purple-to-orchid gradient controls (#dc56f0 to #a52bd9), pink #e292f4 and ember orange #f48d30 accents, beige parchment scrolls with dark ink, faint purple smoke at the edges. Role colours mark people, never containers.

STORY: The jury sees the hall, the Koning hands the floor to a Raadslid, that Raadslid answers from their chair with sourced IDs, open questions shrink, the Koning closes, the hall turns into the feast and the Verdict scroll unrolls.

FIRST VIEWPORT: Full-bleed raadszaal render under a dark plum veil; centred gothic title "De Council van Achrona" in light blue with shadow, one line of story, one purple gradient button "Open de zitting". On start the veil lifts and the camera pushes in; the 16:9 hall fills the viewport between a slim top bar (title, live state, seven portrait cards) and the bottom HUD (turn count, prev/play/next, timeline in role colours, speed, logboek).

FORM: pinned whole by the user; seed: none (pinned). "Maak het in deze stijl maar met 3d design" (style of https://www.2026.hackthefuture.be/challenges/the-council-of-achrona); "het begint met de raadzaal png en dat met tekst berichten naast hun karakters krijgen wnr ze praten"; "animatie het begint met de raadzaal"; "doe die rare cirkel weg bij elke kop". Signature interaction: speech scroll anchored to the speaker's seat with typewriter reveal, auto-advancing, live-following. Motion grammar: one veil-lift and push-in on start; scroll unroll per turn; hall-to-feast crossfade with confetti at the Verdict.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
