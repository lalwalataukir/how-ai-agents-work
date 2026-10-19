# Quiz

A one-question check at the end of each stage, with lettered options and instant feedback.

## Use
- `accent` 1.5px border and `radius-xl`; the label "Check your understanding · Stage N" is mono `accent`.
- Options are buttons with a mono letter (A, B, C). After a choice, the right option gets `.right` (`final`) and a wrong pick `.wrong` (`bad`); feedback text explains why in one or two sentences.
- Feedback starts with the verdict in words ("Right.", "Not quite."), so colour is never the only signal.
- Quizzes are hidden when printing.

## Source
`how-ai-agents-work.html` `.quiz`. Static rendition of the guides' markup, styled by `components/bundle.css`.
