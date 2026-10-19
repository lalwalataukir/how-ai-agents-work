# ModuleCard

A module on the home page: big number, title, summary, what's inside, loop chips, meta and a CTA. The whole card is the link.

## Use
- Two-up in `.modules` (min 420px); the deep-dive modules use the three-up variant (`.modules.three`, min 300px, 2.4rem numerals).
- The numeral is the module's real number in reading order, in display 3rem `accent`.
- Chips (`.c-plan`, `.c-act`, `.c-obs`, `.c-chain`) name what the module covers, coloured by loop phase.
- `.meta` lists reading time and demo count in mono. One `.cta` per card.
- The `h2 a::after` overlay makes the whole card clickable; hover lifts it 2px and turns the border `accent`.

## Source
`index.html` `.module`. Static rendition of the guides' markup, styled by `components/bundle.css`.
