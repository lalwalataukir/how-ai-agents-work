# SearchDialog

Site-wide search across all modules and the glossary, opened from the top bar with `/` or `Ctrl+K`.

## Use
- A 680px dialog on `surface` with `radius-xl` and `shadow-dialog`, over a dark scrim. Full-screen under 600px.
- Each result shows where it lives (mono, `accent`, uppercase), a display-face heading with the section in muted, and a snippet with the match marked (`accent-soft` fill, 2px accent underline).
- The selected result gets `accent-soft` and a 1.5px accent outline. Footer lists the keys.
- The index comes from `search-index.js`; rebuild it with `python3 build-search.py` after editing a page.

## Source
`search.js` (`.gs-*`). The preview shows the dialog without its fixed scrim. Static rendition of the guides' markup, styled by `components/bundle.css`.
