# rankinbc Claude Code plugins

A [Claude Code](https://claude.com/claude-code) plugin marketplace. Add it once,
then install whichever plugins you want:

    /plugin marketplace add rankinbc/claude-plugins

| Plugin | What it does | Platform | Install |
|---|---|---|---|
| [recursive-research](plugins/recursive-research) | Researches a subject to a chosen depth and leaves a structured, source-tagged knowledge base, with its strongest claims checked against their sources | Windows, macOS, Linux (Python 3.9+) | `/plugin install recursive-research@rankinbc` |
| [secret-courier](plugins/secret-courier) | Moves secrets between stores and targets by name, so Claude never sees a value; fail-closed guard hooks keep Claude's tools away from secret files | **Windows only** (PowerShell 7, Python 3.11+) | `/plugin install secret-courier@rankinbc` |
| [project-scaffolder](plugins/project-scaffolder) | Guided `/project-scaffolder:new-project` interview that researches, plans and scaffolds a structured, PRP-driven project in your current folder | Windows, macOS, Linux | `/plugin install project-scaffolder@rankinbc` |

Start a new Claude Code session after installing; plugins load at startup.
Each plugin's README covers its requirements, usage and development.

## Layout

    .claude-plugin/marketplace.json   the marketplace ("rankinbc")
    plugins/<name>/                   one folder per plugin, with its own .claude-plugin/plugin.json
    .github/workflows/<name>.yml      one CI workflow per plugin, run only when that plugin changes

## Releases

Plugins are versioned independently. A release is tagged `<plugin>--vX.Y.Z`,
for example `recursive-research--v0.3.0` or `secret-courier--v0.1.1`, and the
version in that plugin's `.claude-plugin/plugin.json` matches the tag.

## Moved from

These plugins used to live in their own repositories. Their full history was
imported here; the old repositories are no longer where development happens.

- [rankinbc/RecursiveResearch](https://github.com/rankinbc/RecursiveResearch) → [`plugins/recursive-research`](plugins/recursive-research)
- [rankinbc/Secret-Courier-Claude](https://github.com/rankinbc/Secret-Courier-Claude) → [`plugins/secret-courier`](plugins/secret-courier)
- [rankinbc/claude-project-scaffolder](https://github.com/rankinbc/claude-project-scaffolder) → [`plugins/project-scaffolder`](plugins/project-scaffolder)

If you installed from an old repository, switch over:

    /plugin marketplace remove recursive-research      # or: secret-courier
    /plugin marketplace add rankinbc/claude-plugins
    /plugin install <name>@rankinbc

## License

MIT. See [`LICENSE`](LICENSE). Plugins that carry their own `LICENSE` file are
also MIT.
