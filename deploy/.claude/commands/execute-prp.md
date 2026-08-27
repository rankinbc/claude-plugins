# Execute PRP

## PRP File: $ARGUMENTS

Implement whatever the PRP describes. PRPs can produce different kinds of deliverables — read the PRP first to understand what you're building.

**Arguments:**
- `$1` — path to the PRP (required)
- `--component <name>` *(optional)* — if the PRP has multiple `## Component:` sections (option-B v1 mega-PRPs from `/new-project`), build only the named one. Others stay as stubs. Lifecycle stage flips to `"built"` only when ALL components end up with `scaffold_state: "built"`.

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
- **Read `components/<name>/CLAUDE.md` for every component the PRP builds or touches.** Those files carry the pattern gotchas that shape the implementation. Claude Code loads them automatically once you open a file in the folder, but planning happens first — read them now, before step 2.
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
- If a gate fails because a secret is unset, don't try to read or write `.env` — it's deny-listed. Run `pwsh -File scripts/secure/Test-Readiness.ps1` to see which keys are missing by name, then tell the user to run `.\scripts\secure\Set-ProjectSecrets.ps1` in their own terminal and pause until they confirm.
- Any new dependency goes in the root `pyproject.toml`, never a new component-local manifest.

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

### 7. Advance the lifecycle and clean up scaffolder state

**Only after a successful archive in step 6.** Skip entirely if `.scaffolding/manifest.json` does not exist (non-scaffolder project, or `/execute-prp` was re-run on an already-built project).

Two flavors:
- **Full build** (no `--component` flag, OR all components are now `"built"` after this run) — update the manifest, then **delete the entire `.scaffolding/` folder** and strip the README status banner. The project ends up clean with zero scaffolder footprint.
- **Partial build** (`--component <name>` used, other components still stubs) — update only the named component's `scaffold_state` to `"built"`, leave `lifecycle.stage` at `"plan"`, and leave `.scaffolding/` in place. No README changes.

1. **Update `.scaffolding/manifest.json`** — flip the appropriate component(s) `scaffold_state` to `"built"`; if all components are now built, also flip `lifecycle.stage` to `"built"` and append a history entry. Use Python to preserve formatting:

   ```bash
   python - <<'PY'
   import json, datetime, pathlib
   p = pathlib.Path(".scaffolding/manifest.json")
   m = json.loads(p.read_text())
   # Replace BUILT_COMPONENTS with the names you just finished building.
   # For a full build, list every component in the manifest.
   BUILT_COMPONENTS = [<names from this run>]
   for c in m.get("components", []):
       if c["name"] in BUILT_COMPONENTS:
           c["scaffold_state"] = "built"
   all_built = all(c.get("scaffold_state") == "built" for c in m.get("components", []))
   if all_built and m.get("lifecycle", {}).get("stage") != "built":
       m["lifecycle"]["stage"] = "built"
       m["lifecycle"].setdefault("history", []).append({
           "stage": "built",
           "at": datetime.date.today().isoformat(),
           "by": "/execute-prp",
       })
   p.write_text(json.dumps(m, indent=2) + "\n")
   print("ALL_BUILT" if all_built else "PARTIAL")
   PY
   ```

2. **If and only if the above printed `ALL_BUILT`, clean up scaffolder state:**

   a. **Strip the README status banner.** Remove the entire block from `<!-- status:begin -->` through `<!-- status:end -->` (inclusive of both markers) from `README.md`. If the markers are missing, skip silently.

   b. **Delete `.scaffolding/` entirely.**
      ```bash
      rm -rf .scaffolding/
      ```
      (Windows: `Remove-Item -Recurse -Force .scaffolding` in PowerShell, or `rmdir /S /Q .scaffolding` in cmd.)

   c. **Announce the transition:**

      > Lifecycle: plan → **built**. All components built; `.scaffolding/` removed and README banner stripped. The project is now in its clean, ready-to-use state.

   If the result was `PARTIAL`, instead announce:

      > Component `<name>` built. Manifest updated; other components still stubs. Project remains in `"plan"` stage until all components are built.

### 8. Reference back

Archived PRPs live at `PRPs/archive/<date>_<slug>.md` — still readable, just out of the main `PRPs/` listing. Grep them if you need context on historical work.

---

## Notes

- If validation fails repeatedly, use the error patterns documented in the PRP. If those don't help, research the specific error and update the PRP's gotchas section for future use.
- The archive move is intentionally one-way at the command level. If you need to un-archive (e.g., to resume work you thought was done), `mv` it back to `PRPs/` manually.
