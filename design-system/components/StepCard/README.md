# StepCard

One step of an agent run in the demo timeline: number, kind pill, title, and the thought, call or result.

## Use
- `.step` > `.step-h` (`.step-n` "Step 3", a LoopPhase `.kind`, `.step-t` title), then content.
- Variants: `.s-think` fills with `think-soft`; `.s-final` gets a 1.5px `final` border; `.s-halt` a 1.5px `bad` border for a run that stopped; `.s-bad` a 1px `bad` border for a flagged step.
- Thoughts are italic `ink`. Tool calls use `.call`. Quoted page text uses `.extract` (3px `observe` left rule).
- New steps animate in with a short 6px rise; reduced motion turns it off.

## Source
`how-ai-agents-work.html` `.step`. Static rendition of the guides' markup, styled by `components/bundle.css`.
