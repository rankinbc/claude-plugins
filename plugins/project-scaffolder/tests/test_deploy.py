"""Tests for the secret guard that new-project copies into every generated project.

Runs deploy/.claude/hooks/block_secret_access.py through its launcher, the same
way Claude Code does, and checks the verdicts: exit 2 blocks, exit 0 allows.
"""
import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOOKS = ROOT / "deploy" / ".claude" / "hooks"
GUARD = HOOKS / "block_secret_access.py"
LAUNCHER = HOOKS / "run_python_hook.sh"
SH = shutil.which("sh")

# Commands that reach for a secret file, including the review's bypass attempts.
BLOCK = ['less .env',
 'cp .env x',
 'python -c "open(\'.env\')"',
 'cat .e*',
 'cat .en?',
 'cat .[e]nv',
 'gc .env',
 'Get-Content ./.env',
 'type ..\\proj\\.env',
 'cat .ENV',
 'cat .Env',
 "cat '.e''nv'",
 'python -c "open(\'.\'+\'env\')"',
 'python -c "print(open(r\'.e\' \'nv\').read())"',
 'cp .env.example .env',
 'cat components/x/.env',
 'cat .env.production',
 'cat ".env"',
 'Get-Content -Path .\\.env',
 'cat .env.example.bak',
 'sed -n p .env;',
 'awk 1 .env',
 'cat .env\\.local',
 "rg '' -g '.env'",
 'cat /proj/.ENV.local',
 'tar cf - .e* | tar xOf -',
 'cat .\\env',
 'cat .e`nv',
 'cat .e\\nv',
 'cat .*',
 'grep -r KEY .',
 'grep -rn KEY',
 'grep -rn foo',
 'grep -R --include=*.py x .',
 'grep KEY -r .',
 'grep -r KEY /',
 'grep -r KEY ~',
 'grep -r KEY $HOME',
 'grep -r -e KEY',
 'grep -r KEY components /',
 'grep -r -A 3 KEY',
 'rg --hidden KEY',
 'rg -uu KEY',
 'rg -u KEY .',
 'findstr /s KEY *',
 'gci -Recurse | Select-String KEY',
 'Get-ChildItem -r | Get-Content',
 'find . -type f -exec cat {} +',
 'find . | xargs grep KEY',
 'ls certs/*.pem',
 'cat secrets.json']

# Ordinary commands, and the committed templates, stay allowed.
ALLOW = ['cat .env.example',
 'cat .env.sample',
 'cat .env.template',
 'source .venv/bin/activate',
 'node -e "console.log(process.env.X)"',
 'cat foo.environment',
 'cat env.json',
 'ls -la',
 'ls *',
 'cat *.md',
 'ls *.*',
 'python -m pytest',
 'python -m pip install -e ".[dev]"',
 'ruff check .',
 'git add .',
 'grep -n foo components/a/main.py',
 'grep -rn foo components/',
 'grep -r -e KEY components tests',
 'grep -r -c KEY components',
 'grep -r -A 3 KEY components',
 'rg --hidden KEY components',
 'rg -n KEY .',
 'rg KEY components',
 'pwsh -File scripts/secure/Test-Readiness.ps1',
 'powershell -NoProfile -ExecutionPolicy Bypass -File scripts/secure/Test-Readiness.ps1',
 'python -c "import os; print(os.environ.get(\'X\'))"',
 "find . -name '*.py'",
 'echo hello > out.txt; env | wc -l',
 'pytest -k env',
 'git status',
 'Get-ChildItem -Recurse -Filter *.py',
 'streamlit run components/a/app.py']

# (tool, tool_input, expected exit code) for the file and search tools.
FILE_CASES = [('Read', {'file_path': 'C:/p/.env'}, 2),
 ('Read', {'file_path': 'C:\\p\\.ENV.local'}, 2),
 ('Read', {'file_path': '/p/.env.example'}, 0),
 ('Read', {'file_path': '/p/README.md'}, 0),
 ('Write', {'file_path': '/p/.env'}, 2),
 ('Edit', {'file_path': '/p/components/a/secrets.json'}, 2),
 ('Glob', {'pattern': '**/.env*'}, 2),
 ('Glob', {'pattern': '**/*.py'}, 0),
 ('Glob', {'pattern': '**/*'}, 0),
 ('Grep', {'pattern': 'KEY', 'path': '.env'}, 2),
 ('Grep', {'pattern': '\\.env', 'path': 'components'}, 0),
 ('Grep', {'pattern': 'x', 'glob': '*.{ts,tsx}'}, 0),
 ('Grep', {'pattern': 'x', 'glob': '.env*'}, 2),
 ('Read', {'file_path': '/p/.venv/lib/x.py'}, 0)]

# Payloads the guard cannot make sense of must block, not allow.
MALFORMED = [
    ("", 2),
    ("not json", 2),
    ("[]", 2),
    ('"str"', 2),
    (json.dumps({"tool_name": "Bash", "tool_input": "cat .env"}), 2),
    (json.dumps({"tool_name": "Bash", "tool_input": {"command": ["cat", ".env"]}}), 2),
    (json.dumps({"tool_name": "Bash", "tool_input": {"command": "ls"}}), 0),
]


def run(payload):
    data = payload if isinstance(payload, str) else json.dumps(payload)
    proc = subprocess.run([SH, str(LAUNCHER), str(GUARD)], input=data,
                          capture_output=True, text=True, timeout=30)
    return proc.returncode, proc.stderr


@unittest.skipIf(SH is None, "needs sh (Git Bash on Windows)")
class SecretGuardTest(unittest.TestCase):
    def test_blocks_secret_reads(self):
        for command in BLOCK:
            with self.subTest(command=command):
                self.assertEqual(run({"tool_name": "Bash", "tool_input": {"command": command}})[0], 2)

    def test_allows_ordinary_commands(self):
        for command in ALLOW:
            for tool in ("Bash", "PowerShell"):
                with self.subTest(tool=tool, command=command):
                    code, err = run({"tool_name": tool, "tool_input": {"command": command}})
                    self.assertEqual(code, 0, err)

    def test_file_and_search_tools(self):
        for tool, tool_input, expected in FILE_CASES:
            with self.subTest(tool=tool, tool_input=tool_input):
                self.assertEqual(run({"tool_name": tool, "tool_input": tool_input})[0], expected)

    def test_malformed_payloads_fail_closed(self):
        for payload, expected in MALFORMED:
            with self.subTest(payload=payload[:40]):
                self.assertEqual(run(payload)[0], expected)

    def test_denial_message_is_ascii(self):
        code, err = run({"tool_name": "Bash", "tool_input": {"command": "cat .env"}})
        self.assertEqual(code, 2)
        self.assertTrue(err.isascii())

    def test_missing_guard_script_blocks(self):
        proc = subprocess.run([SH, str(LAUNCHER), str(HOOKS / "missing.py")],
                              input=json.dumps({"tool_name": "Bash", "tool_input": {"command": "ls"}}),
                              capture_output=True, text=True, timeout=30)
        self.assertEqual(proc.returncode, 2)


class DeployFilesTest(unittest.TestCase):
    def test_settings_split(self):
        shared = json.loads((ROOT / "deploy" / ".claude" / "settings.json").read_text(encoding="utf-8"))
        local = json.loads((ROOT / "deploy" / ".claude" / "settings.local.json").read_text(encoding="utf-8"))
        self.assertIn("Read(./.env)", shared["permissions"]["deny"])
        self.assertNotIn("allow", shared["permissions"])
        self.assertIn("PreToolUse", shared["hooks"])
        self.assertEqual(set(local), {"permissions"})
        self.assertEqual(set(local["permissions"]), {"allow"})

    def test_launcher_has_lf_endings(self):
        self.assertNotIn(b"\r", LAUNCHER.read_bytes())

    def test_plugin_root_references_exist(self):
        for md in [*(ROOT / "commands").glob("*.md"), *(ROOT / "agents").glob("*.md")]:
            for ref in re.findall(r"\$\{CLAUDE_PLUGIN_ROOT\}/([A-Za-z0-9_./-]+)", md.read_text(encoding="utf-8")):
                with self.subTest(file=md.name, ref=ref):
                    self.assertTrue((ROOT / ref.rstrip(".")).exists())

    def test_commands_have_no_positional_placeholders(self):
        # Claude Code replaces $0, $1 ... in command text, which breaks shell templates.
        for md in (ROOT / "commands").glob("*.md"):
            with self.subTest(file=md.name):
                self.assertIsNone(re.search(r"\$[0-9]", md.read_text(encoding="utf-8")))


if __name__ == "__main__":
    unittest.main()
