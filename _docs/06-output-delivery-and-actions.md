# Output, Delivery, and Actions

## Output contracts

The system should emit a small set of explicit output modes.

### `digest`
A multi-section briefing used for morning/evening editions.

### `mini_digest`
A shorter contextual output used for triggers such as location arrival or gap windows.

### `warning`
A high-urgency message such as leave-now or schedule risk.

### `nudge`
A low-urgency suggestion that is worth surfacing but not demanding.

### `action_prep`
An execution-adjacent output that prepares a side effect but stops before approval-required completion.

### `deep_brief`
A domain-aware, expert-depth synthesis used when a topic deserves more than a shallow summary.
It should include:
- key claim
- why it matters
- source ladder
- unresolved questions
- concise explanation tuned to the user's understanding

### `source_audit`
A source-focused output that explains:
- what the primary source is
- what remains secondary/tertiary
- what was confirmed
- what is still uncertain

## Morning digest structure

Suggested sections:
- `today`
- `people`
- `incoming`
- `followup`
- `resurface`
- optional `feed_updates` when relevant and within quota

## Evening digest structure

Suggested sections:
- `today`
- `followup`
- `tomorrow`
- `tonight`
- `resurface`

## Event-driven outputs

### Feed update
Good shapes:
- short update when relevance is clear and scope is small
- `deep_brief` when the update is important and needs deeper synthesis
- `source_audit` when authority/verification itself is the main issue

### Leave-now
Good shape:
- current risk state
- travel estimate
- recommended departure timing
- optionally one contextual reminder, not a long digest

### Operational mail
Good shape:
- what changed
- why it matters today
- immediate next step if any

### Location dwell
Good shape:
- one low-urgency reason such as stopped-moving, meal-window, or snack-window
- exactly enough local context for the next moment
- map link retained
- no broad digest dump

## Execution levels

### Level 0
Observe only. No user-visible output.

### Level 1
Send information / suggestions only.

### Level 2
Prepare action artifacts without finalizing.

### Level 3
Perform side effect after user approval.

## Approval gate

The system should make it easy to stop at the boundary before irreversible effects.
This is especially important for:
- commerce
- reservations
- messaging
- financial actions

## Delivery adapters

Keep delivery separate from synthesis.
Potential adapters:
- Slack
- Telegram
- local file / markdown
- email summary
- future app/web UI

Current Slack direct-delivery expectation:
- convert markdown links like `[label](url)` into Slack-native `<url|label>` formatting before posting
- split oversized digest posts into a parent message plus threaded replies instead of sending one giant block

## Formatting rule

The same candidate bundle may be rendered differently depending on output mode.
A source audit should not look like a morning digest section.
A deep brief should not look like a leave-now warning.
That is why rendering belongs after synthesis, not before it.

## Key product stance

Do not over-notify.
The system wins when the user feels:
- “that was the right moment”
- “that was exactly enough context”
- “that was grounded in the best available source”
not when it shows all available evidence.
