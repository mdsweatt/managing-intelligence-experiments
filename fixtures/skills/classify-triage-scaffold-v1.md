# Skill — Support-Ticket Triage Classifier (frozen procedure · placebo)

Apply the priority definitions given in the user's message to the ticket, and output the single best-matching label. Use **only** those definitions; add no criteria of your own.

## How to decide
- Match the ticket against each definition (P1_Critical, P2_High, P3_Normal, P4_Low) as written.
- Choose the one label whose definition the ticket matches in full. If more than one matches in full, choose the higher severity.

## Output
- Output exactly one label from the fixed set, verbatim — no punctuation, no surrounding text.

<!-- Placebo note: task #4's baseline prompt already carries the label set + definitions and is
near-deterministic. This skill only re-states the matching rule (adds no new criteria, asks for no
hidden multi-step reasoning), so the prediction is that it moves neither tokens nor the label —
the H5 confound guard. -->
