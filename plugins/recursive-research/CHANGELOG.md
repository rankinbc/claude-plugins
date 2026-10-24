# Changelog

All notable changes to recursive-research are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow semantic
versioning. Releases are tagged `recursive-research--vX.Y.Z`.

## 0.3.0 - Unreleased

Moved into the [rankinbc/claude-plugins](https://github.com/rankinbc/claude-plugins)
marketplace. Install with `/plugin install recursive-research@rankinbc`.

### Fixed

- A source that cannot be reached this time (timeout, DNS failure, dropped
  connection, server error) no longer counts as a failed check. The claim keeps
  its tag, is reported as unchecked, and is checked again on the next run.
  Only lasting failures (gone, forbidden) are cached.
- A claim downgraded because its source is gone keeps its quote and address in
  the rewritten tag.
- A `source_file` inside `research/` no longer verifies a claim: the knowledge
  base cannot cite itself. `source_file` must be a regular file of at most 5 MB.
- Tags inside fenced or inline code are no longer verified or rewritten.
- The HTML renderer no longer crashes on a NUL character, and code inside a link
  label renders.
- Brief ids match whole words (`d1` no longer matches `d10`); brief paths are
  absolute.
- A response with an unknown charset falls back to UTF-8 instead of counting as
  unreachable.

### Security

- Fetches open only `http` and `https` addresses, on every redirect hop, and
  refuse hosts that resolve to private, loopback, link-local or reserved
  addresses, including after the connection is made.

### Changed

- Fetching is bounded: 15 seconds per page, 60 seconds per run, six pages at a
  time, so a run finishes well inside Claude Code's two-minute command limit.
  Pages not reached in time are checked on the next run.
- SKILL.md and the README name `python` or `py -3` on Windows.

## 0.2.0 - 2026-10-05

- HTML report of the knowledge base, in light and dark, with links between
  knowledge files.
- Scorecard: claims by tier, what is verified, unknowns and conflicts.
- Every PRIMARY claim in the knowledge base is checked against its source, not
  only stage 4 findings.
- A quoted passage in a PRIMARY tag may contain square brackets.

## 0.1.0 - 2026-10-05

First pre-release.

- Coordinator skill with staged references, researcher and organizer agents,
  script-rendered briefs and a progress view.
- Every PRIMARY quote is checked against its source.
- Python 3.9+, standard library only; reads UTF-16 files. MIT license.
