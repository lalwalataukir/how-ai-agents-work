# GlossaryTerm

An inline term with a dotted accent underline that opens a short definition popover.

## Use
- Mark the first use of a term in a section: `<button class="term" aria-expanded="false">context window</button>`.
- The popover shows the term in the display face, then one or two plain sentences. It uses `shadow-pop`, the only floating shadow in the system.
- Every term also appears on the Reference page, which is searchable.

## Source
`how-ai-agents-work.html` (`.term`, `#termPop`). The guides position the popover absolutely under the term; the preview places it in flow and uses the class `.term-pop`. Static rendition of the guides' markup, styled by `components/bundle.css`.
