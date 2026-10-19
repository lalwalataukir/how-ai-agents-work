# Button

Buttons that drive the demos: step, autoplay, reset, approve, and the module CTA on the home page.

## Use
- `.btn` is the default: `surface` fill, 1.5px `line` border that turns `accent` on hover, `radius-md`.
- `.btn-primary` (accent fill, `accent-ink` label) marks the one main action in a control row, such as "Next step". Never more than one per row.
- `.btn-sm` for secondary controls inside lessons and approval rows.
- Disabled buttons drop to 45% opacity with a not-allowed cursor; keep them in place so the row does not jump.
- `.cta` is a link styled as a primary button, used once per home-page module card ("Open module 1").
- Pair a shortcut with `.kbd` ("Space" to step).
- Labels say exactly what happens: "Next step", "Autoplay", "Reset", "Approve", "Block". No icons-only buttons.

## Source
`how-ai-agents-work.html` (`.btn`, `.btn-primary`, `.btn-sm`, `.kbd`) and `index.html` (`.cta`). Static rendition of the guides' markup, styled by `components/bundle.css`.
