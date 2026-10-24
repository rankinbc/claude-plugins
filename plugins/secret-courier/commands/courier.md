---
description: Secret courier - move a secret by name (exists, prompt, copy, inject, run, test, sinks, sweep, doctor) without the value ever passing through Claude
argument-hint: <command> [args]   e.g. exists github-pat | prompt github-pat | sinks | sweep --dry-run | doctor
allowed-tools: Bash
---

Run the secret-courier CLI with the arguments the user gave, through the plugin's wrapper:

```
"${CLAUDE_PLUGIN_ROOT}/scripts/courier.cmd" $ARGUMENTS
```

With no arguments, run `doctor` and then `names`, and summarise: which names exist and where, which
plaintext copies (`sinks`) are outstanding, and whether the hooks are wired and fail closed.

Rules: the command prints one status line and never a value. Report the status in plain words. If the user
asks for a value, or offers to paste one, run `prompt <name>` instead and point them at the console that
opens. If a command returns `error`, show the reason and stop; never retry with a different store or path to
get around a refusal. Load the `secret-courier` skill for the decision table.
