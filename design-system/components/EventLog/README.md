# EventLog

The engineer's view of a run: a timestamped mono log on `code-bg`, each event coloured by loop phase.

## Use
- `.log` > `div` per event: `.t` time (muted), then the event name in its phase class: `.e-model` think, `.e-tool` act, `.e-res` observe, `.e-run` final, `.e-bad` bad, `.e-human` accent.
- Event names are snake_case, as an engineer would see them.

## Source
`how-ai-agents-work.html` `.log`. Static rendition of the guides' markup, styled by `components/bundle.css`.
