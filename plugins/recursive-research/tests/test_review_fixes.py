"""Fixes from the pre-publish review: transient fetch failures, self-citation, local file limits,
code in Markdown, exact task ids, the time budget, address checks, charsets and brief paths."""
import functools
import http.server
import os
import socket
import threading
import time
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

from helpers import REPO, WorkspaceCase, proposal
from rrlib import briefs, mdlite, provenance, store, verify

PAGE = "<p>A frame MUST NOT exceed 16384 bytes.</p>"
QUOTE = "A frame MUST NOT exceed 16384 bytes."
URL = "https://example.org/spec"


class FetchCase(WorkspaceCase):
    def setUp(self):
        super().setUp()
        self.calls = []
        for name in ("FETCH", "BUDGET", "ALLOW_PRIVATE"):
            self.addCleanup(setattr, verify, name, getattr(verify, name))

    def fetch_with(self, behaviour):
        def fetch(url):
            self.calls.append(url)
            return behaviour(url)
        verify.FETCH = fetch

    def md(self, text, rel="knowledge/tree/README.md"):
        return self.write(rel, text)


class TransientFailureTests(FetchCase):
    def test_a_timeout_leaves_the_tag_intact_and_the_next_run_confirms_it(self):
        def flaky(url):
            if len(self.calls) == 1:
                raise TimeoutError("timed out")
            return PAGE
        self.fetch_with(flaky)
        text = f'Cap [PRIMARY: "{QUOTE}" {URL}].\n'
        path = self.md(text)
        first = verify.sweep(self.ws)
        self.assertEqual((first["verified"], first["downgraded"], first["unchecked"]), (0, 0, 1))
        self.assertIn("run verify again", first["next"])
        self.assertEqual(path.read_text(encoding="utf-8"), text)
        self.assertFalse(verify.is_checked(self.ws, path))
        self.assertFalse((self.ws / "sources" / "index.json").is_file() and
                         URL in store.read_json(self.ws / "sources" / "index.json"))
        verify.reset_run()  # the next command
        second = verify.sweep(self.ws)  # the file is unchanged, but had an unchecked claim
        self.assertEqual((second["files_checked"], second["verified"], second["unchecked"]), (1, 1, 0))
        self.assertEqual(path.read_text(encoding="utf-8"), text)
        self.assertTrue(verify.is_checked(self.ws, path))
        self.assertEqual(len(self.calls), 2)

    def test_within_one_run_a_failed_address_is_not_tried_again(self):
        self.fetch_with(lambda url: (_ for _ in ()).throw(ConnectionResetError("reset")))
        self.md(f'A [PRIMARY: "{QUOTE}" {URL}]. B [PRIMARY: "{QUOTE}" {URL}].\n')
        self.assertEqual(verify.sweep(self.ws)["unchecked"], 2)
        self.assertEqual(self.calls, [URL])

    def test_a_server_error_is_retried_but_a_missing_page_is_kept(self):
        codes = {"https://a.example/x": 503, "https://b.example/x": 404}

        def fail(url):
            raise urllib.error.HTTPError(url, codes[url], "err", None, None)
        self.fetch_with(fail)
        for url in codes:
            self.assertTrue(verify.check(self.ws, {"quote": QUOTE, "source_url": url}))
        index = store.read_json(self.ws / "sources" / "index.json")
        self.assertEqual(list(index), ["https://b.example/x"])
        self.assertIsInstance(verify.check(self.ws, {"quote": QUOTE, "source_url": "https://a.example/x"}),
                              verify.Pending)

    def test_an_error_cached_by_an_older_version_is_tried_again(self):
        store.write_json(self.ws / "sources" / "index.json",
                         {URL: {"file": None, "error": "TimeoutError: timed out"}})
        self.fetch_with(lambda url: PAGE)
        self.assertIsNone(verify.check(self.ws, {"quote": QUOTE, "source_url": URL}))

    def test_a_tag_downgraded_for_its_source_keeps_its_quote_and_address(self):
        def gone(url):
            raise urllib.error.HTTPError(url, 410, "Gone", None, None)
        self.fetch_with(gone)
        path = self.md(f'Cap [PRIMARY: "{QUOTE}" {URL}]. Next [EXPERT].\n')
        self.assertEqual(verify.sweep(self.ws)["downgraded"], 1)
        after = path.read_text(encoding="utf-8")
        self.assertEqual(after, f'Cap [SECONDARY: "{QUOTE}" {URL}; was PRIMARY, source unreachable]. Next [EXPERT].\n')
        self.assertEqual(provenance.scan_markdown(after)["counts"]["SECONDARY"], 1)

    def test_a_json_entry_waiting_on_its_source_stays_primary_and_unconfirmed(self):
        self.fetch_with(lambda url: (_ for _ in ()).throw(TimeoutError("slow")))
        path = self.write("knowledge/tree/sizes.json", {"cap": {"tier": "PRIMARY", "quote": QUOTE, "source_url": URL}})
        self.assertEqual(verify.sweep(self.ws)["unchecked"], 1)
        entry = store.read_json(path)["cap"]
        self.assertEqual((entry["tier"], entry["verified"]), ("PRIMARY", False))
        self.assertNotIn("downgraded_from", entry)

    def test_a_roster_value_waiting_on_its_source_is_not_downgraded_or_listed_as_verified(self):
        self.fetch_with(lambda url: (_ for _ in ()).throw(TimeoutError("slow")))
        path = self.write("knowledge/entities/message_type.json", {"type": "MessageType", "entities": [
            {"name": "HELLO", "properties": {"reply": "WELCOME"}, "provenance": "PRIMARY",
             "evidence": {"quote": QUOTE, "source_url": URL}}]})
        self.assertEqual(verify.sweep(self.ws)["unchecked"], 1)
        entity = store.read_json(path)["entities"][0]
        self.assertEqual((entity["provenance"], entity["verified"]), ("PRIMARY", []))
        verify.reset_run()
        self.fetch_with(lambda url: PAGE)
        verify.sweep(self.ws)
        entity = store.read_json(path)["entities"][0]
        self.assertEqual(entity["verified"], ["reply"])
        self.assertNotIn("verify_notes", entity)


class LocalSourceTests(FetchCase):
    def test_a_file_inside_the_workspace_does_not_verify_itself(self):
        leaf = self.md("Made up [PRIMARY: \"this sentence was invented by the model itself\" knowledge/tree/leaf.md]\n",
                       "knowledge/tree/leaf.md")
        result = verify.verify_markdown(self.ws, leaf)
        self.assertEqual((result["verified"], result["downgraded"]), (0, 1))
        self.assertIn("source is the knowledge base itself", leaf.read_text(encoding="utf-8"))
        for source in (str(leaf), leaf.as_posix(), "../test-subject/knowledge/tree/leaf.md"):
            problem = verify.check(self.ws, {"quote": "this sentence was invented by the model itself",
                                             "source_file": source})
            self.assertIn("cannot cite itself", problem)

    def test_another_subjects_workspace_is_also_refused(self):
        other = self.root / "other" / "knowledge" / "spec.md"
        other.parent.mkdir(parents=True)
        other.write_text(PAGE, encoding="utf-8")
        self.assertIn("cannot cite itself", verify.check(self.ws, {"quote": QUOTE, "source_file": str(other)}))

    def test_a_relative_path_is_read_from_the_project_folder(self):
        self.write_source("spec.html", PAGE)
        self.assertIsNone(verify.check(self.ws, {"quote": QUOTE, "source_file": "local/spec.html"}))

    def test_a_folder_or_an_oversized_file_is_not_read(self):
        folder = self.root.parent / "local" / "dir"
        folder.mkdir(parents=True)
        self.assertIn("not a regular file", verify.check(self.ws, {"quote": QUOTE, "source_file": str(folder)}))
        big = self.write_source("big.txt", PAGE)
        with mock.patch.object(verify, "MAX_BYTES", 10):
            self.assertIn("larger than", verify.check(self.ws, {"quote": QUOTE, "source_file": str(big)}))


class CodeTests(FetchCase):
    def test_tags_in_code_are_neither_checked_nor_rewritten_nor_counted(self):
        self.fetch_with(lambda url: "")
        text = ("Write a claim like `[PRIMARY: \"quote\" url]` or:\n\n"
                "```\nX [PRIMARY: \"not a real quote at all, an example\" https://e.example/a]\n```\n\n"
                "~~~md\nY [PRIMARY]\n~~~\n\nReal [PRIMARY].\n")
        path = self.md(text)
        result = verify.verify_markdown(self.ws, path)
        self.assertEqual((result["verified"], result["downgraded"]), (0, 1))
        self.assertEqual(path.read_text(encoding="utf-8"),
                         text.replace("Real [PRIMARY]", "Real [SECONDARY: was PRIMARY, no quote given]"))
        self.assertEqual(self.calls, [])
        self.assertEqual(provenance.scan_markdown(text)["counts"]["PRIMARY"], 1)

    def test_a_tilde_fence_renders_as_code(self):
        out = mdlite.render("~~~\n[PRIMARY] *x*\n~~~\nafter")
        self.assertIn("<pre><code>[PRIMARY] *x*</code></pre>", out)
        self.assertIn("<p>after</p>", out)


class MdliteTests(unittest.TestCase):
    def test_a_nul_in_the_text_does_not_crash_or_survive(self):
        out = mdlite.inline("text \x005\x00 more `c`")
        self.assertNotIn("\x00", out)
        self.assertIn("<code>c</code>", out)

    def test_code_inside_a_link_label_is_rendered(self):
        self.assertEqual(mdlite.inline("[label `code`](https://a.b)"),
                         '<a href="https://a.b" rel="noopener noreferrer">label <code>code</code></a>')

    def test_code_inside_a_quote_shows_as_its_own_text_in_the_badge(self):
        out = mdlite.inline('[PRIMARY: "call `open()` before reading the file" https://a.b]')
        self.assertNotIn("\x00", out)
        self.assertIn("call `open()` before", out)
        self.assertIn('href="https://a.b"', out)


class BriefTests(WorkspaceCase):
    def test_a_task_id_matches_only_whole_ids(self):
        self.start_wave([proposal("p1")])
        boot = store.load_plan(self.ws)["sessions"][-2]
        self.write(f"sessions/{boot}/coordination_brief.md", "- p1: owns framing\n- p10: owns retries\n")
        text = Path(briefs.task_brief(self.ws, "p1")["brief"]).read_text(encoding="utf-8")
        self.assertIn("- p1: owns framing", text)
        self.assertNotIn("p10", text)

    def test_brief_paths_and_the_workspace_are_absolute(self):
        here = os.getcwd()
        self.addCleanup(os.chdir, here)
        os.chdir(self.root.parent)
        ws = store.workspace("research", "test-subject")
        self.fill_plan()
        from rrlib import tasks
        tasks.add_session(ws, "survey")
        info = briefs.task_brief(ws, "s01")
        self.assertTrue(Path(info["brief"]).is_absolute())
        os.chdir(here)  # an agent working somewhere else still finds both
        text = Path(info["brief"]).read_text(encoding="utf-8")
        self.assertIn(self.ws.resolve().as_posix(), text)


class BudgetTests(FetchCase):
    def test_sources_are_fetched_at_the_same_time(self):
        def slow(url):
            time.sleep(0.4)
            return PAGE
        self.fetch_with(slow)
        self.md("".join(f'C{i} [PRIMARY: "{QUOTE}" https://e.example/{i}].\n' for i in range(6)))
        started = time.monotonic()
        self.assertEqual(verify.sweep(self.ws)["verified"], 6)
        self.assertLess(time.monotonic() - started, 1.5)

    def test_sources_not_reached_in_time_are_left_unchecked_not_failed(self):
        verify.BUDGET = 0.3
        release = threading.Event()
        self.addCleanup(release.set)

        def stuck(url):
            release.wait(5)
            return PAGE
        self.fetch_with(stuck)
        text = "".join(f'C{i} [PRIMARY: "{QUOTE}" https://e.example/{i}].\n' for i in range(3))
        path = self.md(text)
        started = time.monotonic()
        result = verify.sweep(self.ws)
        self.assertLess(time.monotonic() - started, 2)
        self.assertEqual((result["unchecked"], result["downgraded"]), (3, 0))
        self.assertEqual(path.read_text(encoding="utf-8"), text)
        while verify._remaining() > 0:  # a timed wait can return a tick early on Windows
            time.sleep(0.02)
        self.assertIn(verify.OUT_OF_TIME, verify.check(self.ws, {"quote": QUOTE, "source_url": "https://e.example/9"}))


def addresses(*ips):
    return lambda host, port, *a, **k: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, port)) for ip in ips]


class AddressTests(FetchCase):
    def test_only_http_and_https_are_opened(self):
        for url in ("file:///etc/passwd", "ftp://example.org/x", "gopher://x", "http:///nohost"):
            with self.assertRaises(verify.Refused, msg=url):
                verify.check_address(url)

    def test_private_local_and_metadata_addresses_are_refused(self):
        for url in ("http://127.0.0.1/", "http://169.254.169.254/latest/meta-data/", "http://10.1.2.3/",
                    "http://192.168.0.1/", "http://[::1]/", "http://[::ffff:127.0.0.1]/", "http://0.0.0.0/"):
            with self.assertRaises(verify.Refused, msg=url):
                verify.check_address(url)

    def test_a_name_that_resolves_to_a_private_address_is_refused(self):
        with mock.patch.object(socket, "getaddrinfo", addresses("93.184.216.34", "10.0.0.5")):
            with self.assertRaises(verify.Refused):
                verify.check_address("https://sneaky.example/")
        with mock.patch.object(socket, "getaddrinfo", addresses("93.184.216.34")):
            verify.check_address("https://example.org/")

    def test_a_refused_address_downgrades_and_keeps_the_evidence(self):
        path = self.md(f'X [PRIMARY: "{QUOTE}" http://169.254.169.254/latest].\n')
        verify.verify_markdown(self.ws, path)
        self.assertEqual(path.read_text(encoding="utf-8"),
                         f'X [SECONDARY: "{QUOTE}" http://169.254.169.254/latest; was PRIMARY, source address refused].\n')
        self.assertFalse((self.ws / "sources" / "index.json").is_file()
                         and store.read_json(self.ws / "sources" / "index.json"))

    def serve(self, handler_class):
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler_class)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        return f"http://127.0.0.1:{server.server_address[1]}"

    def test_a_redirect_to_another_scheme_is_refused(self):
        class Redirect(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(302)
                self.send_header("Location", "file:///etc/passwd")
                self.end_headers()

            def log_message(self, *args):
                pass
        verify.ALLOW_PRIVATE = True
        base = self.serve(Redirect)
        with self.assertRaises(verify.Refused):
            verify._http_get(base + "/x")

    def test_a_redirect_to_a_private_address_is_refused(self):
        verify.ALLOW_PRIVATE = False
        redirect = verify._Redirects()
        req = mock.Mock(full_url="https://example.org/a")
        with self.assertRaises(verify.Refused):
            redirect.redirect_request(req, None, 302, "Found", {}, "http://127.0.0.1:8080/admin")

    def test_an_unknown_charset_falls_back_to_utf8(self):
        class Bogus(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                body = PAGE.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=no-such-charset")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass
        verify.ALLOW_PRIVATE = True
        base = self.serve(Bogus)
        self.assertIsNone(verify.check(self.ws, {"quote": QUOTE, "source_url": base + "/p"}))
        self.assertEqual(verify.decode("caf\xe9".encode("utf-8"), "x-unknown"), "caf\xe9")


class SkillDocTests(unittest.TestCase):
    def test_the_python_command_works_on_windows_too(self):
        text = (REPO / "skills" / "recursive-research" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("py -3", text)


if __name__ == "__main__":
    unittest.main()
