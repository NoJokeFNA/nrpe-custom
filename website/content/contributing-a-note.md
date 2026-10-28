# Contribute a field note

Useful field notes describe a real sequence of observations, including mistakes
and unresolved questions. They are not endorsements or promises that a procedure
works on every host.

## What to include

- Date, actual distribution/service pack, architecture and relevant tool versions.
- The initial symptom and the smallest test that helped narrow it down.
- Reviewed commands, expected/observed output and the actual outcome.
- Which changes were temporary, how they were cleaned up, and what remains untested.
- Attribution only to people who consent to being named. An anonymous project note is fine.

Remove real hostnames, private addresses, credentials, keys, company certificates
and confidential configuration. Use documentation addresses such as `192.0.2.10`.
Never invent commands, successful outcomes or personal testimonials.

## How a note reaches the website

Add a reviewed English Markdown file under `website/content/`, with a title,
date/platform line and introductory paragraph. The field-notes index and search
include it automatically. Follow the project's [contribution workflow](../../CONTRIBUTING.md):
topic branch, review and integration into develop. Publication to `gh-pages`
is a separate explicit maintainer action. There is no public submission form or
unmoderated comment storage on this static website.
