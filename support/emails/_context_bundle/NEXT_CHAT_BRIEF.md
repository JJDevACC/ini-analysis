# Email Context Bundle for Next Codex Chat

Use this bundle as the starting point for project context reconstruction from email artifacts.

## Scope
- Includes extracted content from `email-01.eml` through `email-05.eml`.
- Includes bodies (`text/plain`, `text/html`), inline images, and attachments.
- Detects chronology and basic overlap signals (subject grouping, duplicate message/body hashes).

## Project Intent (User Hint)
- Future objective: convert existing R pipeline code to Python with equivalent functionality and automation support.
- This bundle only prepares context and artifacts; it does not perform migration.

## Start Here
- Machine index: `support/emails/_context_bundle/context-index.json`
- Chronology table: `support/emails/_context_bundle/chronology.csv`

## Recommended Read Order
- 1. email-02.eml (2026-02-06T17:52:48+00:00)
- 2. email-03.eml (2026-02-06T19:44:19+00:00)
- 3. email-04.eml (2026-02-12T14:40:09+00:00)
- 4. email-05.eml (2026-02-20T03:19:16+00:00)
- 5. email-01.eml (2026-02-23T14:14:26+00:00)

## Extracted Artifact Locations
- `email-02.eml` -> `support/emails/email-02.extracted`
- `email-03.eml` -> `support/emails/email-03.extracted`
- `email-04.eml` -> `support/emails/email-04.extracted`
- `email-05.eml` -> `support/emails/email-05.extracted`
- `email-01.eml` -> `support/emails/email-01.extracted`

## Notes on Overlap / Numbering
- File numbering (`email-01`..`email-05`) may not match chronological order.
- Use chronology from `date_utc` and `chronological_index`, not filename order.
- Quoted prior messages inside bodies can make content appear duplicated across files.

## Suggested Next-Chat Prompt Seed
```text
Read support/emails/_context_bundle/context-index.json first, then process emails in chronological_index order.
Use extracted artifacts under each *.extracted/parts folder (bodies, inline images, CSV attachments).
Build a migration plan from R to Python preserving behavior and adding automation, but do not code yet.
```
