# Box

The basic content card: a titled block of explanation inside a two- or three-column grid.

## Use
- `.box` on `surface` with a `line` border and `radius`; `.box.tint` drops the border and sits on `surface-2` for a quieter companion block.
- Lay boxes out in `.grid.g2` (min 300px) or `.grid.g3` (min 240px) with a `space-14` gap; they stack to one column on phones.
- Inside: an optional Tag, an `h4`, then body text or a `ul.clean` list.
- Never add a coloured left border or a shadow to a box.

## Source
`how-ai-agents-work.html` `.box`, `.grid`. Static rendition of the guides' markup, styled by `components/bundle.css`.
