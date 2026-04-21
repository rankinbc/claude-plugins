# Execute PRP

## PRP File: $ARGUMENTS

Implement whatever the PRP describes. PRPs can produce different kinds of deliverables — read the PRP first to understand what you're building.

---

## Deliverable types

| PRP describes | You produce |
| --- | --- |
| A feature | Working code in the project (with tests) |
| A data analysis | Analysis scripts + output artifacts (report, charts) |
| A tool / integration | Working tool + its tests + any config files it needs |

The PRP's output location is stated in the PRP itself. Respect it.

---

## Execution Process

### 1. Load PRP

- Read the specified PRP file completely
- Understand all context, requirements, and validation gates
- Extend research if you hit gaps — don't guess when you can verify
- Use sub-agents for any exploration that would generate noise

### 2. ULTRATHINK

Before writing any code:

- Create a comprehensive task plan. Use TodoWrite to track it.
- Break complex tasks into smaller, testable steps.
- Identify patterns in existing code to follow.

### 3. Execute the plan

- Implement each task in order
- Run validation gates as you hit them — don't skip to the end and hope
- If a task reveals the PRP is wrong, stop and discuss before proceeding

### 4. Validate

- Run every validation gate in the PRP
- Fix failures, re-run until all pass
- Don't mock failing tests into passing. Fix the underlying issue.

### 5. Complete

- Verify every success-criteria checkbox from the PRP
- Run the final validation suite end-to-end
- Report completion status to the user with what was built and where it lives
- Re-read the PRP one more time to make sure nothing was missed

### 6. Archive the PRP

**Only if execution completed successfully** (all validation gates passed, success criteria met):

Move the PRP from `PRPs/<slug>.md` to `PRPs/archive/<YYYY-MM-DD>_<slug>.md`:

```bash
mkdir -p PRPs/archive
mv "PRPs/<slug>.md" "PRPs/archive/$(date +%Y-%m-%d)_<slug>.md"
```

This keeps `PRPs/` a clean list of *active* plans. Completed PRPs are preserved in `archive/` for future reference but won't surface in day-to-day exploration.

**Do NOT archive** if:
- Any validation gate failed
- You stopped mid-execution (user interrupt, blocker, crash)
- Success criteria are partially met

Failed/interrupted PRPs stay in `PRPs/` so the next session can pick them up.

### 7. Reference back

Archived PRPs live at `PRPs/archive/<date>_<slug>.md` — still readable, just out of the main `PRPs/` listing. Grep them if you need context on historical work.

---

## Notes

- If validation fails repeatedly, use the error patterns documented in the PRP. If those don't help, research the specific error and update the PRP's gotchas section for future use.
- The archive move is intentionally one-way at the command level. If you need to un-archive (e.g., to resume work you thought was done), `mv` it back to `PRPs/` manually.
