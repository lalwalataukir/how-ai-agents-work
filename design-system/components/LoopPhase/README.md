# LoopPhase

The colour code of the agent loop: think, act (call a tool), observe (read the result), finish. It is the guides' signature and appears as kind pills, a phase rail, diagram nodes and log events.

## Use
- One hue per phase, always in this order: `think` → `act` → `observe` → `final`. Two more kinds sit outside the loop: `bad` (blocked, failed, injected) and `accent` (a human approval).
- Kind pills (`.kind` + `.k-think`, `.k-call`, `.k-res`, `.k-final`, `.k-bad`, `.k-human`) label a timeline step. The pill always carries the word, so the colour is never the only signal.
- The phase rail (`.phases` > `.phase.plan|act|observe|finish`) shows where the run is; only the current phase gets `.is-on`.
- Langfuse (`fuse`) shares the observe hue, and `ok` / `warn` alias `final` / `act`, so a status reads the same across modules.
- In the light theme `final` on `final-soft` is 4.3:1, just under 4.5:1 for small text. Keep pill text weight 500 and do not shrink it below .72rem.

## Source
`how-ai-agents-work.html` (`.kind`, `.k-*`, `.phase`). Static rendition of the guides' markup, styled by `components/bundle.css`.
