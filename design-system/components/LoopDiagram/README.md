# LoopDiagram

The SVG diagram of the agent loop. As the demo runs, the node for the current phase lights up in its phase colour.

## Use
- Inside `figure` > `.diagram`, with a `figcaption` in muted.
- Nodes are `g.node.plan|act|observe|finish` with a `rect` and text; add `.is-on` to the active one. Idle nodes stay `surface` with a `line` stroke.
- Edges are 1.5px `muted`; a dashed `bad` edge (`.edge-dash`) shows a path an attack takes.
- Every fill and stroke comes from a class bound to a token, so the diagram follows the theme.

## Source
`how-ai-agents-work.html` (`figure .diagram`, `svg .node`). Static rendition of the guides' markup, styled by `components/bundle.css`.
