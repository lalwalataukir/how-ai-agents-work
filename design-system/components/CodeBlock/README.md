# CodeBlock

Code samples, with one line highlighted as the demo steps through them, plus the inline "now running" strip and tool-call snippets.

## Use
- `pre.code` with one `.ln` span per line. `.is-on` highlights the active line (`accent-soft` fill, 3px `accent` left rule).
- Syntax: `.k` keywords in `think`, `.s` strings in `observe`, `.c` comments in `muted`. No other colours.
- `.codenow` is a one-line strip in a demo's header that shows the call being made now.
- `.call` shows a tool call in a timeline step; the function name is `act`, or `bad` when it was blocked.

## Source
`how-ai-agents-work.html` (`pre.code`, `.codenow`, `.call`). Static rendition of the guides' markup, styled by `components/bundle.css`.
