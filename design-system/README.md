# Agent Field Guides design system

Agent Field Guides is a set of interactive explainers that teach product managers how AI agents are designed, built, tested, secured and shipped. Every module follows one running example, a research-assistant agent, and every demo is a scripted simulation. The look is a dark field manual: a near-black violet ground, one violet accent, and four loop colours that mark what the agent is doing.

## Content fundamentals

**Audience.** Product managers who work with engineers. Explain mechanisms in plain words, then name the term of art. Never assume they write code; always show the code an engineer would see next to the explanation.

**Voice.** Plain, direct and calm. Short declarative sentences. Address the reader as "you" and the team as "your team"; the guide speaks as "we" only for the running example ("Our research assistant…").

- Do: "An agent is an LLM that works in a loop. It decides on an action, uses a tool to carry it out, looks at the result, and decides again, until the goal is met."
- Do: "Start with the simplest thing that works. Use an agent only for the part of the task that is truly open-ended."
- Do: "Choose the lowest level that handles your real cases."
- Don't: hype ("revolutionary", "supercharge"), exclamation marks, emoji, or jokes.

**Casing.** Sentence case for every heading, button and label ("Decide whether you need an agent at all", "Next step"). Uppercase only through the mono `eyebrow` and `tag` styles, which set it in CSS; write the text in sentence case.

**Structure words.** Sections are stages, numbered because they are a real sequence: "Stage 1 · Ideation", "Stage 2 · Design". The middle dot `·` separates a kicker's parts. Arrows `→` mark onward links ("LangChain, LangGraph & Langfuse →"). Callouts lead with a bolded phrase ending in a full stop: "Plain definition.", "Why this matters.", "You've seen this pattern before."

**Honesty.** Every demo says what is fake, up front: "Simulation. No real AI model or web searches are used." Example web addresses are made up and look it. Prices and timings are labelled illustrative. The guides are independent explainers and say they are not affiliated with LangChain, LangGraph, LangSmith or Langfuse.

**Numbers.** Use real units: tokens, dollars to three decimals for a run ("$0.021"), seconds, p50 and p95. Thousands take commas ("3,412 tokens").

## Visual foundations

### Colour

The system is dark-first. `dark` is the first theme and the default whatever the OS says; `light` is opt-in through the theme button, stored in `localStorage` as `guides.theme`, and applied as `data-theme="light"` on `<html>`. Every colour comes from a token; component CSS never names a hex value.

- **Ground and text.** Page on `bg`. Raised objects on `surface`; quieter fills on `surface-2`; code on `code-bg`. Text is `ink`, secondary text `muted`. Both read on all four grounds in both themes.
- **Accent.** `accent` is the one brand hue: links, the primary button, the active rail stage, focus rings, quiz borders, module numerals. Text on an accent fill is `accent-ink`, never literal white. Tint behind accent text is `accent-soft`. Use the accent sparingly: one primary button per control row, one accent tag per group.
- **The agent loop.** Four phase colours carry the guides' central idea and always run in this order: `think` (the model reasons) → `act` (a tool call) → `observe` (a tool result) → `final` (the answer). `bad` marks a block, failure or injection; `accent` marks a human approval. Each has a `-soft` fill for pills and highlighted steps. A phase colour always travels with its word.
- **Tools.** LangChain is `chain` (an alias of `accent`), LangGraph is `graph` (pink-violet), Langfuse is `fuse` (an alias of `observe`, because tracing watches the results). `b1` (orange) marks a forked branch or edited checkpoint in LangGraph time travel.
- **Status and priority.** `ok` and `warn` alias `final` and `act`. The metrics module ranks with `p0` (alias of `bad`), `p1` (alias of `act`) and `p2` (pale violet).
- **Hairlines.** `line` is decorative and low-contrast on purpose. Controls that must be found get a fill or text, and their border turns `accent` on hover and focus.

### Type

Three Google Fonts families, loaded in one request:

```html
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500..800&family=Atkinson+Hyperlegible:ital,wght@0,400;0,700;1,400&family=IBM+Plex+Mono:wght@400;500&display=swap">
```

- `display` (Bricolage Grotesque, 700–800): headings, module numerals, card titles, formulas, takeaways. Tight leading (1.12–1.15) and -0.01em tracking; `text-wrap: balance`. Module h1 is `page-title`, stage h2 is `section-title`, both fluid with `clamp()`.
- `body` (Atkinson Hyperlegible, 400/700 and italic): all running text at 17px / 1.6, kept to 68ch. Ledes are `lede` in `muted` with the key phrase in `ink`. Agent thoughts in the demo are italic.
- `mono` (IBM Plex Mono, 400/500): eyebrows, tags, phase pills, priority badges, code, logs, status bars and every number that changes. Use `font-variant-numeric: tabular-nums` wherever digits line up.

### Space and layout

- A module is one column, `page-max` 1120px (home and reference: `home-max` 1080px), with a side gutter of at least `space-16` that also clears the phone's safe-area insets.
- Page anatomy, top to bottom: TopBar, hero (eyebrow, h1, lede, hint line), the live demo console, then stage sections in order (each opens with eyebrow, h2 and intro, and ends with a Quiz), the common mistakes, the cheat sheet, NextModule, footer.
- Stage sections are separated by a `line` top border and `space-56` above. Blocks inside a stage sit `space-28` apart; boxes in a grid sit `space-14` apart.
- Grids use `repeat(auto-fit, minmax(min(100%, N), 1fr))` so they collapse to one column on phones. The demo console switches its three panels to tabs under 860px.

### Shape, borders and depth

- Radii by size of object: `radius-xs` keys, `radius-sm` inline code and markers, `radius-md` buttons and inputs, `radius` (10px) boxes, tables, code and callouts, `radius-lg` home cards, `radius-xl` the demo console, quizzes, the cheat sheet and the search dialog. `radius-pill` for chips, tags and phase pills.
- Borders, not shadows, separate objects: 1px `line` for cards, 1.5px for controls and emphasised cards (quiz, final step). Only floating things cast a shadow: `shadow-pop` for the glossary and tool popovers, `shadow-dialog` for search.
- No gradients, no coloured left-border accents on cards (the only left rules are the active code line and quoted extracts), no emoji.

### Motion and states

- Motion is small and functional: timeline steps rise 6px as they appear (0.28s), home cards lift 2px on hover, memory sections flash `accent-soft` when the agent writes to them. `prefers-reduced-motion` turns all of it off.
- Hover turns a border or text `accent`. Disabled controls drop to 45% opacity.
- Keyboard focus is a solid 2.5px `accent` outline, 2px offset (3px on the home page). Never remove it.
- Print hides the top bar, demos and quizzes and prints black on white.

## Iconography

The guides use no icon set and no emoji. Meaning is carried by words, colour pills and a few text glyphs:

- `→` onward links and next-module bars; `↗` (added by `tool-links.js`) external docs links; `·` separator in kickers.
- Demo transport glyphs `▶`, `⏸`, `↺` sit next to a text label, never alone. `✓` and `×` appear only beside a word.
- One inline SVG: the search magnifier (24px grid, 2.2 stroke, round caps, `currentColor`), shown at 15px in the top bar and 18px in the dialog.
- Diagrams are hand-built inline SVG whose fills and strokes are classes bound to tokens (see LoopDiagram).

There is no logo. The name "Agent Field Guides" is set in `display` at weight 800.

## Using this system

- Load the Google Fonts link above, then `tokens.css`, then `components/bundle.css`. Token names match the custom properties in the guides' pages (`--bg`, `--accent`, `--think`, `--font-display`, `--radius` …), so module CSS works unchanged.
- Components are plain HTML and CSS classes taken from the module pages; there is no JavaScript bundle. Each component's README gives its markup and rules.
- New modules copy the page anatomy above, keep the running research-assistant example, open every demo with a SimBanner, and end every stage with a Quiz.

## Not synced

Built from the local checkout of `how-ai-agents-work` (the generated HTML pages, `search.js`, `tool-links.js`). The `serve.js` source pages named in the repo README are not in this checkout. Per-page local variables (`--c`, `--cs`) are left out. Demo internals with no reuse outside one module (the context-budget bar, rollout simulator, retrieval tuner, checkpoint timeline, memory panel) are not components here. Components ship as static renditions with `bundle.css`, not as a script bundle.
