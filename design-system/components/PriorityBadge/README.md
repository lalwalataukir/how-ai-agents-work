# PriorityBadge

P0 / P1 / P2 labels from the metrics module, as a small badge and as a priority card.

## Use
- `.pb.p0` launch blocker (`p0` = `bad`), `.pb.p1` core health (`p1` = `act`), `.pb.p2` optimisation (`p2`, a pale violet).
- Badges sit before a metric's name. Corner radius is 5px, squarer than tags, so priorities don't read as loop phases.
- The card `.prio` sets `--c` inline to the priority token and draws a 4px top rule in it. Its `.rule` line states the review cadence in mono.
- Keep the labels "P0", "P1", "P2"; the card title gives the meaning in words.

## Source
`metrics.html` (`.pb`, `.prio`). Static rendition of the guides' markup, styled by `components/bundle.css`.
