# ToolLink

An automatic link on every mention of a tool (LangChain, LangGraph, Langfuse, MCP…) to its official docs, with a hover card.

## Use
- `tool-links.js` wraps mentions in body text; it skips code, buttons, the top bar and demos. Add tools in its `TOOLS` list, not by hand.
- The link keeps the text colour with an `accent` underline and a small ↗.
- The hover card shows the kind (mono, accent), the name, and the docs domain.

## Source
`tool-links.js`. The source tints the underline with `color-mix(accent 60%, transparent)`; the preview uses plain `accent`. Static rendition of the guides' markup, styled by `components/bundle.css`.
