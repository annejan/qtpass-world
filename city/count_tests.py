#!/usr/bin/env python3
"""Count Qt Test functions per suite over QtPass's history.

count_tests.py QTPASS_REPO [REV] [OUTDIR]   -> OUTDIR/tests.json, tags.json, commits.json

REV defaults to main; the film uses acce8abde (10 November 2026). OUTDIR
defaults to data. Sampled at every first-parent commit up to REV that
touched tests/, and once a week besides, so the CI count (workflow files:
the searchlights) follows too. A test function is a `void name();`
declared under `private slots:` (or `private Q_SLOTS:`) in a test source,
minus the fixtures (init, cleanup, initTestCase, cleanupTestCase) and the
`_data` providers.

tests.json: [{"t": unix, "rev": sha, "suites": {name: n}, "ci": n}, ...]
tags.json: [[tag, unix], ...] for every v* tag, oldest first.
commits.json: [[unix, kind], ...] for every commit up to REV (the traffic),
kind from the subject: l10n, ci, test, fix, docs, tidy, feat or other.
"""
import json
import os
import re
import subprocess
import sys

REPO = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/Projects/QtPass")
REV = sys.argv[2] if len(sys.argv) > 2 else "main"
OUT = sys.argv[3] if len(sys.argv) > 3 else "data"
FIXTURES = {"init", "cleanup", "initTestCase", "cleanupTestCase"}
SLOT = re.compile(r"^\s*void\s+(\w+)\s*\(\s*\)\s*;", re.M)
ACCESS = re.compile(r"^\s*(public|private|protected)(\s+(slots|Q_SLOTS))?\s*:", re.M)
WEEK = 7 * 86400


def git(*a):
    return subprocess.run(["git", "-C", REPO, *a], capture_output=True, text=True,
                          errors="replace").stdout


def tests_in(text):
    names = []
    parts = ACCESS.split(text)  # [pre, access, ' slots', 'slots', body, ...]
    for i in range(1, len(parts), 4):
        access, slots, body = parts[i], parts[i + 2], parts[i + 3]
        if access == "private" and slots:
            names += [n for n in SLOT.findall(body)
                      if n not in FIXTURES and not n.endswith("_data")]
    return names


def suites_at(sha):
    suites = {}
    for f in git("ls-tree", "-r", "--name-only", sha).split("\n"):
        if f.startswith("tests/") and re.search(r"tst_\w+\.(cpp|h)$", f):
            names = tests_in(git("show", f"{sha}:{f}"))
            if names:
                s = re.search(r"tst_(\w+)\.", f).group(1)
                suites[s] = suites.get(s, 0) + len(set(names))
    return suites


def ci_at(sha):
    flows = git("ls-tree", "--name-only", sha, ".github/workflows/").split()
    root = git("ls-tree", "--name-only", sha).split()
    return (len([f for f in flows if f.endswith((".yml", ".yaml"))])
            + sum(f in root for f in (".travis.yml", "appveyor.yml", ".appveyor.yml")))


# What a commit was, from its subject: the colour of its snake. First match.
KINDS = [
    ("l10n", r"translat|weblate|l10n|locali[sz]ation|\.ts\b|lupdate"),
    ("ci", r"^ci\b|^ci:|bump |dependabot|workflow|github action|\bCI\b|appveyor|travis"),
    ("test", r"\btests?\b|^test|coverage|tst_"),
    ("fix", r"\bfix|bug|crash|^revert|regression"),
    ("docs", r"readme|changelog|\bdocs?\b|faq|doxygen|typo|comment"),
    ("tidy", r"refactor|clean|simplif|rename|move|extract|style|format|lint|clang|prettier|tidy"),
    ("feat", r"^feat|\badd|support|implement|new |allow|option|enable"),
]


def kind_of(subject):
    return next((k for k, p in KINDS if re.search(p, subject, re.I)), "other")


def revs(*paths):
    log = git("log", "--first-parent", "--format=%H %ct", REV, "--", *paths)
    return [(l.split()[0], int(l.split()[1])) for l in log.split("\n") if l.strip()][::-1]


def main():
    every = revs()
    picked, last = {}, None
    for sha, t in every:
        if last is None or t - last >= WEEK:
            picked[sha] = t
            last = t
    picked[every[-1][0]] = every[-1][1]
    for sha, t in revs("tests"):
        picked[sha] = t
    out = [{"t": t, "rev": sha[:9], "suites": suites_at(sha), "ci": ci_at(sha)}
           for sha, t in sorted(picked.items(), key=lambda x: x[1])]
    os.makedirs(OUT, exist_ok=True)
    json.dump(out, open(os.path.join(OUT, "tests.json"), "w"))
    end = out[-1]["t"]
    tags = git("for-each-ref", "--sort=creatordate",
               "--format=%(refname:short) %(creatordate:unix)", "refs/tags").split("\n")
    json.dump([[n, int(t)] for n, t in (l.split() for l in tags if l.startswith("v"))
               if int(t) <= end + 2 * 86400],
              open(os.path.join(OUT, "tags.json"), "w"))
    commits = sorted([int(t), kind_of(subject)] for t, subject in
                     (l.split("\t", 1) for l in git("log", "--format=%ct%x09%s", REV).split("\n")
                      if l.strip()))
    json.dump(commits, open(os.path.join(OUT, "commits.json"), "w"))
    print(len(out), "samples,", sum(out[-1]["suites"].values()), "tests in",
          len(out[-1]["suites"]), "suites at", REV)


if __name__ == "__main__":
    main()
