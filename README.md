<h1 align="center">rankinbc / claude-plugins</h1>

<p align="center">
  <strong>Claude Code plugins for deep research, safe secret handling and well-built new projects.</strong><br>
  One marketplace, three plugins, each tested on every change.
</p>

<p align="center">
  <a href="https://github.com/rankinbc/claude-plugins/actions/workflows/recursive-research.yml"><img src="https://github.com/rankinbc/claude-plugins/actions/workflows/recursive-research.yml/badge.svg" alt="recursive-research tests"></a>
  <a href="https://github.com/rankinbc/claude-plugins/actions/workflows/secret-courier.yml"><img src="https://github.com/rankinbc/claude-plugins/actions/workflows/secret-courier.yml/badge.svg" alt="secret-courier tests"></a>
  <a href="https://github.com/rankinbc/claude-plugins/actions/workflows/project-scaffolder.yml"><img src="https://github.com/rankinbc/claude-plugins/actions/workflows/project-scaffolder.yml/badge.svg" alt="project-scaffolder tests"></a>
  <a href="https://github.com/rankinbc/claude-plugins/actions/workflows/marketplace.yml"><img src="https://github.com/rankinbc/claude-plugins/actions/workflows/marketplace.yml/badge.svg" alt="marketplace check"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green" alt="MIT license"></a>
  <a href="https://claude.com/claude-code"><img src="https://img.shields.io/badge/claude%20code-plugin%20marketplace-6e40c9" alt="Claude Code plugin marketplace"></a>
</p>

## Install

Inside [Claude Code](https://claude.com/claude-code), add the marketplace once:

    /plugin marketplace add rankinbc/claude-plugins

Then install whichever plugins you want, and start a new session (plugins load at startup):

    /plugin install recursive-research@rankinbc
    /plugin install secret-courier@rankinbc
    /plugin install project-scaffolder@rankinbc

## The plugins

| Plugin | What it does | Runs on |
|---|---|---|
| [**recursive-research**](plugins/recursive-research) | Researches a subject to the depth you choose and leaves a structured, source-tagged knowledge base, with its strongest claims checked against their sources by a script | Windows, macOS, Linux · Python 3.9+ |
| [**secret-courier**](plugins/secret-courier) | Lets Claude use your API keys and tokens by name without ever seeing a value; fail-closed guard hooks keep Claude's tools away from secret files | **Windows only** · PowerShell 7, Python 3.11+ |
| [**project-scaffolder**](plugins/project-scaffolder) | A guided `/project-scaffolder:new-project` interview that researches, plans and scaffolds a structured, plan-driven project in your current folder | Windows, macOS, Linux |

### recursive-research: research you can check

Name a subject and say what you need it for. Claude plans the research, sends out
teams of researcher agents in stages you approve, and leaves a knowledge base in
your project with a report you can open in a browser. Every claim carries a tier
saying how well it is supported, and every top-tier claim carries the exact words
it rests on and where they are. A script opens each source and checks the words
are really there; a claim that fails is downgraded, with the reason recorded.

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="plugins/recursive-research/docs/images/report-dark.png">
    <img src="plugins/recursive-research/docs/images/report-light.png" width="820"
         alt="The research report for a run on the Gemini protocol: a sidebar of branches and catalogue tables, and one branch's overview with a tier badge after each claim.">
  </picture>
</p>

Standard library only, no dependencies. [Read more](plugins/recursive-research#readme).

### secret-courier: Claude uses the name, never the value

You type a secret once at a masked prompt; it is encrypted on your machine. From
then on Claude works with a name (`github-pat`), and the plugin delivers the value
where the job needs it (a child process, a git-ignored config file, an HTTPS
check) and records every plaintext copy so it can be swept.

```
> /courier run --env GITHUB_TOKEN=dpapi:github-pat -- gh release create v1.2.0

Ran gh with GITHUB_TOKEN set in its environment only. The process has exited with code 0 and the
value is gone with it. Nothing was written to disk.
exit 0
```

Guard hooks check every shell command, file read, search and write before it runs,
and refuse anything that would expose a value. If the guard cannot run, the call
is refused. [SECURITY.md](plugins/secret-courier/SECURITY.md) states exactly what
it protects and what it cannot. [Read more](plugins/secret-courier#readme).

### project-scaffolder: start a project with a plan

Run `/project-scaffolder:new-project` in an empty folder and answer a few
questions. The plugin breaks your idea into components, researches each in
parallel, proposes a structure for you to approve, and scaffolds the project:
folder layout, conventions in `CLAUDE.md`, slash commands, a `.env` guard, and a
v1 build plan that `/execute-prp` follows. [Read more](plugins/project-scaffolder#readme).

## How this repository works

    .claude-plugin/marketplace.json   the marketplace ("rankinbc") listing every plugin
    plugins/<name>/                   one self-contained plugin per folder, with its own
                                      README, CHANGELOG, LICENSE and tests
    .github/workflows/<name>.yml      each plugin's CI, run only when that plugin changes
    scripts/check_marketplace.py      checks the marketplace and every manifest agree

- **Independent versions.** Each plugin is versioned on its own. A release is
  tagged `<plugin>--vX.Y.Z` (for example `recursive-research--v0.3.0`), and CI
  refuses a tag that does not match the version in that plugin's
  `.claude-plugin/plugin.json`.
- **Tested where it runs.** recursive-research and project-scaffolder are tested
  on Ubuntu, macOS and Windows; secret-courier on Windows, including its
  PowerShell operations under Pester.
- **No secrets in the tree.** secret-courier scans its own source for
  secret-shaped values in CI.

Working on a plugin? See [CONTRIBUTING.md](CONTRIBUTING.md). Found a security
problem? See [SECURITY.md](SECURITY.md).

## Moved from

These plugins used to live in their own repositories. Their full history was
imported here, and development continues here.

- [rankinbc/RecursiveResearch](https://github.com/rankinbc/RecursiveResearch) → [`plugins/recursive-research`](plugins/recursive-research)
- [rankinbc/Secret-Courier-Claude](https://github.com/rankinbc/Secret-Courier-Claude) → [`plugins/secret-courier`](plugins/secret-courier)
- [rankinbc/claude-project-scaffolder](https://github.com/rankinbc/claude-project-scaffolder) → [`plugins/project-scaffolder`](plugins/project-scaffolder)

If you installed from an old repository, switch over:

    /plugin marketplace remove recursive-research      # or: secret-courier
    /plugin marketplace add rankinbc/claude-plugins
    /plugin install <name>@rankinbc

## License

MIT. See [LICENSE](LICENSE); each plugin also carries its own copy.
