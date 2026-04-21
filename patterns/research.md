# Shape: Research

Pure knowledge work. Gather information, synthesize, produce a written deliverable. Minimal code.

This describes **one component** inside a scaffolded project — `components/<component_name>/`. Project-level infrastructure (CLAUDE.md, INITIAL.md, PRPs/, .claude/, .gitignore, shared data/ and output/) lives at the project root.

## Default stack

- **Markdown** + Claude's web research. That's the whole stack.
- Optionally Python for web scraping if the user needs to pull structured data from many pages.

## Folder structure (component-internal)

```
components/<component_name>/
├── README.md                 # Purpose / inputs / outputs / how to run
├── sources/                  # Raw notes from sources (one file per source or topic)
│   └── .gitkeep
└── scrape.py                 # OPTIONAL: programmatic source collection (only if needed)
```

Reference material the user provides lives under `data/<source_name>/` at the project root. The final synthesis deliverable lands in `output/<component_name>/<YYYY-MM-DD>_<run>/SYNTHESIS.md` — also at the project root.

## No code needed for most

Research components often don't need `.py` files, `requirements.txt`, or test suites. Claude's PRP workflow generates and runs research directly:

- `/generate-prp INITIAL.md` → a research plan (what sources, what questions, what structure for the deliverable)
- `/execute-prp` → Claude does the research and writes the synthesis to `output/<component_name>/<date>_<run>/`

If the user needs to pull data programmatically (e.g., scrape 100 GitHub repos for metrics), then:
- Add a lightweight `scrape.py` using `httpx` or `requests` + `beautifulsoup4`
- Cache responses to `data/<source>/` at the project root so they don't re-scrape on every run

## Gotchas for CLAUDE.md

- **Cite sources**: every factual claim in the deliverable needs a link or reference. "According to the 2024 Stack Overflow survey..." with the URL.
- **Scope discipline**: if they asked for "top 5 tools," compare 5. Don't drift to 15 in pursuit of completeness.
- **Acknowledge uncertainty**: when sources conflict or data is thin, say so explicitly in the deliverable.
- **Executive summary first**: write a one-paragraph TL;DR at the top. The deep analysis comes after.
- **No unsourced claims**: if Claude can't find a source for something, flag it rather than asserting.
- **Date-stamp the research**: frameworks evolve, research goes stale. Note "as of [date]" on findings.

## Validation

```bash
# Research is harder to validate automatically. Some heuristics:
ls output/<component_name>/*/SYNTHESIS.md >/dev/null && echo "Deliverable exists"
grep -rhc "^http" output/<component_name>/*/SYNTHESIS.md   # Has citations
wc -l output/<component_name>/*/SYNTHESIS.md                # Not trivially short
```

## Interview follow-ups

- "What specifically do you want to know — comparison, landscape scan, deep dive on one thing?"
- "Who reads the final writeup? (you, your team, a VP)"
- "What's the deliverable format — markdown report, slide deck content, comparison table, email?"
- "How deep? A 1-page summary, or a 10-page analysis?"
- "Any sources you already know to include? Any to avoid (e.g., 'no vendor marketing pages')?"

## INITIAL.md pre-fill hints

- **FEATURE**: The research question(s) + what the deliverable looks like + length expectation
- **EXAMPLES**: Past research writeups the user liked (if any)
- **DOCUMENTATION**: Specific sources to pull from; forbidden sources
- **OTHER CONSIDERATIONS**: Budget constraints, timezone/freshness requirements, audience's technical level, bias concerns
