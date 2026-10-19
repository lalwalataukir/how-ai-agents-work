# TraceSummary

The four-number header of a Langfuse-style trace: latency, cost, tokens, spans.

## Use
- A 4-column strip with 1px `line` gaps. Values mono with tabular figures, labels in muted .72rem.
- Always the same four, in this order, so traces can be compared at a glance.

## Source
`langfuse.html` `.trace-sum`. Static rendition of the guides' markup, styled by `components/bundle.css`.
