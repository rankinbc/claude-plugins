# Security policy

## Reporting a problem

Please report security problems privately through
[GitHub private vulnerability reporting](https://github.com/rankinbc/claude-plugins/security/advisories/new),
not in a public issue. Include the plugin, its version, your OS and Claude Code
version, and the smallest steps that show the problem. Use made-up values only;
never send a real secret.

You can expect an acknowledgement within a week. Fixes ship as a new release of
the affected plugin, with the problem described in its changelog once users can
update.

## What counts

- **secret-courier:** any way for Claude, or a command Claude runs, to read a
  stored value, a secret file it guards, or to change the guard's own policy.
  Its [SECURITY.md](plugins/secret-courier/SECURITY.md) describes the threat
  model and lists the limits that are already known; a bypass of something it
  claims to protect is in scope.
- **project-scaffolder:** a way past the `.env` guard it installs in new
  projects that does not involve code built to evade it at runtime (the guard
  is documented as a guardrail, not a sandbox).
- **recursive-research:** making the quote check report a claim as verified
  when its source does not contain the quote, or making the fetcher reach
  a private or local address.

## Supported versions

Only the latest release of each plugin receives fixes.
