#!/usr/bin/env python3
"""Checks for the documents agents and Matthew follow. Run: python3 tests/test_docs.py

Standard library only. The documents are LEAD.md, ARCHITECT.md, README.md, the thin skill
(.claude/skills/agent-room/SKILL.md), briefs/*.md and, once it exists, docs/manual/*.md.

- Every `python3 room.py ...` line in them, in a code block or an inline code span, parses with
  room.py's own argument parser, after placeholders are replaced with sample values: OWNER/NAME,
  the room N, M<k> and any other <...>.
- Every relative markdown link in them resolves to a file or directory in this repo. Until
  docs/manual/ exists, links into it are skipped.
- If docs/manual/ exists: every page but README.md has the five sections of v1's page format, as
  headings that contain "When to use", "need first", "Steps", "should see" and "If you don't"
  (or "If it doesn't"); and docs/manual/README.md links every page.
"""
import argparse
import contextlib
import glob
import importlib.util
import io
import os
import re
import shlex
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ROOM = os.path.join(ROOT, "room.py")
MANUAL = os.path.join(ROOT, "docs", "manual")
SKILL = os.path.join(ROOT, ".claude", "skills", "agent-room", "SKILL.md")
REQUIRED = [os.path.join(ROOT, p) for p in ("LEAD.md", "ARCHITECT.md", "README.md", "CHANGELOG.md", "STABLE")] + [SKILL]

SHA = "0123456789abcdef0123456789abcdef01234567"
NUMERIC = {"PR", "pr", "ID", "id", "cursor", "room", "number"}
OPERATORS = set(";&|<>()")
SECTIONS = (
    ("When to use it", r"when to use"),
    ("What you need first", r"need first"),
    ("Steps", r"\bsteps?\b"),
    ("What you should see", r"should see"),
    ("If you don't", r"if (you|it) (don|doesn|didn)|if not\b"),
)


def doc_files():
    files = [os.path.join(ROOT, p) for p in ("LEAD.md", "ARCHITECT.md", "README.md")] + [SKILL]
    files += sorted(glob.glob(os.path.join(ROOT, "briefs", "*.md")))
    files += sorted(glob.glob(os.path.join(MANUAL, "*.md")))
    return [f for f in files if os.path.isfile(f)]


def rel(path):
    return os.path.relpath(path, ROOT)


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


# --- room.py command lines

def logical_lines(text):
    """(line number, text, in_fence) per line; fenced lines ending in a backslash are joined to the next."""
    out, fence, held = [], None, None
    for n, line in enumerate(text.split("\n"), 1):
        mark = re.match(r"\s*(`{3,}|~{3,})", line)
        if mark and (fence is None or mark.group(1).startswith(fence)):
            fence = None if fence else mark.group(1)
            continue
        if fence:
            if held:
                held = (held[0], held[1].rstrip()[:-1] + " " + line.strip())
            else:
                held = (n, line)
            if held[1].rstrip().endswith("\\"):
                continue
            out.append((held[0], held[1], True))
            held = None
        else:
            out.append((n, line, False))
    return out


def commands(path):
    """(line number, command) for every `python3 room.py` with arguments, in code blocks and inline code."""
    found = []
    for n, line, fenced in logical_lines(read(path)):
        texts = [line] if fenced else re.findall(r"`([^`\n]+)`", line)
        for t in texts:
            for m in re.finditer(r"\bpython3 room\.py\b", t):
                cmd = t[m.start():]
                rest = cmd[len("python3 room.py"):].strip()
                if not rest or rest.startswith(("…", "...")):
                    continue  # prose: a bare mention, not a command line
                found.append((n, cmd))
    return found


def sample(name):
    if "sha" in name.lower():
        return SHA
    if name == "command":
        return "gate"
    if len(name) == 1 or name in NUMERIC:
        return "7"
    return "x"


def fill(cmd):
    """Replace placeholders with sample values."""
    cmd = cmd.replace("OWNER/NAME", "SigorMatt/pet-todo")
    cmd = re.sub(r"(?<![\w-])N(?![\w/-])", "4", cmd)
    prev = None
    while prev != cmd:
        prev, cmd = cmd, re.sub(r"<([^<>\s][^<>]*)>", lambda m: sample(m.group(1)), cmd)
    return re.sub(r"(?<=\s)[12]>(&[12])?", ">", cmd)


def argv(cmd):
    """The arguments after `python3 room.py`, up to the first shell operator."""
    lex = shlex.shlex(fill(cmd), posix=True, punctuation_chars=";&|<>()")
    lex.whitespace_split = True
    toks = []
    for t in lex:
        if set(t) <= OPERATORS:
            break
        toks.append(t)
    return toks[2:]


_room = None


def room_module():
    global _room
    if _room is None:
        spec = importlib.util.spec_from_file_location("room_under_doc_test", ROOM)
        _room = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_room)
    return _room


class _Parsed(Exception):
    pass


def parse_error(cmd):
    """None if the command line parses with room.py's argument parser, else why not."""
    try:
        args = argv(cmd)
    except ValueError as e:
        return f"can't split it: {e}"
    room = room_module()
    real = argparse.ArgumentParser.parse_args

    def stop(self, args_=None, namespace=None):
        raise _Parsed(real(self, args, namespace))

    err, saved_argv = io.StringIO(), sys.argv
    argparse.ArgumentParser.parse_args = stop
    sys.argv = ["room.py"]  # argparse's prog in error messages
    try:
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
            room.main()
    except _Parsed:
        return None
    except SystemExit as e:
        if e.code in (0, None):
            return None  # --help
        lines = err.getvalue().strip().splitlines()
        return f"{lines[-1] if lines else f'exit {e.code}'} (args {args})"
    finally:
        argparse.ArgumentParser.parse_args = real
        sys.argv = saved_argv
    return "room.py ran past its argument parser"


# --- links

def strip_code(text):
    lines = [line for _, line, fenced in logical_lines(text) if not fenced]
    return re.sub(r"`[^`\n]*`", "", "\n".join(lines))


def link_targets(text):
    text = strip_code(text)
    targets = re.findall(r"\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)", text)
    targets += re.findall(r"^\s*\[[^\]]+\]:\s*<?(\S+?)>?(?:\s|$)", text, re.M)
    return targets


def resolve(path, target):
    """The local path a relative link points to, or None for a URL or an in-page anchor."""
    if re.match(r"[A-Za-z][A-Za-z0-9+.-]*:", target) or target.startswith("#"):
        return None
    target = re.split(r"[#?]", target, maxsplit=1)[0]
    base = ROOT if target.startswith("/") else os.path.dirname(path)
    return os.path.normpath(os.path.join(base, target.lstrip("/")))


# --- the tests

class Docs(unittest.TestCase):
    def test_required_files_exist(self):
        missing = [rel(p) for p in REQUIRED if not os.path.isfile(p)]
        self.assertFalse(missing, f"missing: {missing}")
        stable = read(os.path.join(ROOT, "STABLE")).split("\n")
        self.assertRegex(stable[0], r"^(main|v\d+\.\d+\.\d+)$", "STABLE names main or a release tag")
        self.assertFalse(any(stable[1:]), "STABLE is one line")

    def test_checker_catches_a_broken_command(self):
        self.assertIsNone(parse_error("python3 room.py merge <PR> --sha <sha> --repo OWNER/NAME"))
        self.assertIsNone(parse_error('python3 room.py say N lead "$(cat /tmp/esc-<n>.md)" && echo ok'))
        self.assertIsNone(parse_error("python3 room.py --help"))
        for bad in ("python3 room.py merge <PR>", "python3 room.py wait N lead --timout 540",
                    "python3 room.py lease grab", "python3 room.py gate M<k>"):
            self.assertIsNotNone(parse_error(bad), bad)

    def test_room_commands_parse(self):
        bad, count = [], 0
        for path in doc_files():
            for n, cmd in commands(path):
                count += 1
                why = parse_error(cmd)
                if why:
                    bad.append(f"{rel(path)}:{n}: {cmd}\n    {why}")
        if bad:
            self.fail("room.py lines that don't parse:\n" + "\n".join(bad))
        self.assertGreater(count, 50, "too few room.py lines found; is the extraction broken?")

    def test_relative_links_resolve(self):
        bad = []
        for path in doc_files():
            for target in link_targets(read(path)):
                local = resolve(path, target)
                if local is None or os.path.exists(local):
                    continue
                if not os.path.isdir(MANUAL) and (local + os.sep).startswith(MANUAL + os.sep):
                    continue  # the manuals land later in M5; links into them are checked once they exist
                bad.append(f"{rel(path)}: {target}")
        if bad:
            self.fail("broken relative links:\n" + "\n".join(bad))

    def test_manual_pages_have_the_five_sections(self):
        if not os.path.isdir(MANUAL):
            self.skipTest("docs/manual/ doesn't exist yet")
        bad = []
        for page in manual_pages():
            heads = re.findall(r"^#{2,3}\s+(.+)$", strip_code(read(page)), re.M)
            for name, pattern in SECTIONS:
                if not any(re.search(pattern, h, re.I) for h in heads):
                    bad.append(f"{rel(page)}: no '{name}' section")
        if bad:
            self.fail("\n".join(bad))

    def test_manual_index_links_every_page(self):
        if not os.path.isdir(MANUAL):
            self.skipTest("docs/manual/ doesn't exist yet")
        index = os.path.join(MANUAL, "README.md")
        self.assertTrue(os.path.isfile(index), "docs/manual/README.md is missing")
        linked = {resolve(index, t) for t in link_targets(read(index))}
        missing = [rel(p) for p in manual_pages() if os.path.normpath(p) not in linked]
        self.assertFalse(missing, f"pages the index doesn't link: {missing}")


def manual_pages():
    return [p for p in sorted(glob.glob(os.path.join(MANUAL, "*.md"))) if os.path.basename(p) != "README.md"]


if __name__ == "__main__":
    unittest.main()
