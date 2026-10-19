# TopBar

The sticky bar at the top of every module: brand, a Home pill, the stage rail, Search and the theme switch, with a 3px reading-progress line under it.

## Use
- One per page, first child of `<main>`. It stays on `bg` with a `line` bottom border, never a shadow.
- The stage rail lists the module's stages in reading order. Each link is `<a href="#stage-id"><span class="n">1</span>Ideation</a>`; the stage in view gets `.is-active` (accent fill, `accent-ink` text).
- The theme button's label names the theme it switches *to* ("Light" while dark). It writes `data-theme` on `<html>` and stores the choice in `localStorage` under `guides.theme`; with nothing stored the guides start dark.
- The brand hides under 640px so the rail keeps its room. The rail scrolls sideways with its scrollbar hidden.
- Search opens with `/` or `Ctrl+K`; the button's label and key hint hide under 760px.

## You provide
Brand text, the Home link (`index.html`), the stage list, and the progress width (scroll ratio) as `style="width:…%"` on `.progress span`.

## Source
`how-ai-agents-work.html` (`.topbar`, `.stages`, `.theme-btn`, `.progress`) and `search.js` (`.gs-btn`). In the guides the bar is `top: env(safe-area-inset-top)` and bleeds past the side gutter with negative margins; this preview drops both. Static rendition of the guides' markup, styled by `components/bundle.css`.
