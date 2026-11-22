#!/usr/bin/env python3
"""Sort the editors' changes to the AI read-aloud texts by kind, per month, into report.json.

Each changed story goes to the OpenAI Decisions API once: per change one choice over the kinds
in codebook.json and a check whether the change mixes kinds. Only totals are written; texts stay private.
"""

import argparse
import collections
import datetime as dt
import difflib
import json
import os
import re
import urllib.error
import urllib.request

MODEL = "gpt-6-luna"
EDITED_MAX = 0.40  # above this share of changed words a story counts as rewritten, as in babbel-analyse
SURE = 0.6  # below this confidence a change counts as unsure, until the editor check sets it
MAX_QUESTIONS = 400  # API limit per request
CODEBOOK = json.load(open(os.path.join(os.path.dirname(__file__) or ".", "codebook.json")))
END = re.compile(r"[.!?][\"'’”)]*$")


def edit_fraction(a, b):
    """Share of words changed, by the longer text."""
    n = max(len(a), len(b))
    if not n:
        return 0.0
    matched = sum(m.size for m in difflib.SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks())
    return (n - matched) / n


def changes(a, b, gap=8):
    """Word spans that changed, merged within a sentence and split at matching sentence ends."""
    parts = []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if op == "equal":
            continue
        ea = [n + 1 for n in range(i1, i2 - 1) if END.search(a[n])]
        eb = [n + 1 for n in range(j1, j2 - 1) if END.search(b[n])]
        if ea and len(ea) == len(eb):
            ii, jj = [i1, *ea, i2], [j1, *eb, j2]
            parts += [[ii[n], ii[n + 1], jj[n], jj[n + 1]] for n in range(len(ii) - 1)]
        else:
            parts.append([i1, i2, j1, j2])
    out = []
    for i1, i2, j1, j2 in parts:
        if out:
            p1, p2, q1, q2 = out[-1]
            near = i1 - p2 <= gap and j1 - q2 <= gap
            ended = any(END.search(t) for t in a[max(p1, p2 - 1):i1]) or any(
                END.search(t) for t in b[max(q1, q2 - 1):j1])
            if near and not ended:
                out[-1][1], out[-1][3] = i2, j2
                continue
        out.append([i1, i2, j1, j2])
    return out


def decide(text, questions):
    body = {"model": MODEL, "input": text, "questions": questions}
    req = urllib.request.Request(
        "https://api.openai.com/v1/decisions", data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}",
                 "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            return json.load(r)["answers"]
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Decisions API {e.code}: {e.read().decode()[:300]}") from e


def label(article, ai, final):
    """Per change: (kind, sure, mixed)."""
    a, b = ai.split(), final.split()
    spans = changes(a, b)
    lines = [f"{n}. [{' '.join(a[i1:i2]) or '(niets)'}] -> [{' '.join(b[j1:j2]) or '(niets)'}]"
             for n, (i1, i2, j1, j2) in enumerate(spans, 1)]
    text = (f"ARTIKEL:\n{article}\n\nAI-TEKST:\n{ai}\n\nUITGEZONDEN TEKST (na de redactie):\n"
            f"{final}\n\nWIJZIGINGEN:\n" + "\n".join(lines))
    kinds = [{"value": k, "description": d} for k, d in CODEBOOK["kinds"].items()]
    questions = []
    for n in range(1, len(spans) + 1):
        questions += [
            {"type": "choice", "name": f"soort{n}", "choices": kinds,
             "instructions": f"Welke soort aanpassing is wijziging {n}?"},
            {"type": "predicate", "name": f"gemengd{n}",
             "instructions": f"Wijziging {n}: {CODEBOOK['gemengd']}"},
        ]
    if not questions or len(questions) > MAX_QUESTIONS:
        return None
    ans = {x["name"]: x for x in decide(text, questions)}
    out = []
    for n in range(1, len(spans) + 1):
        kind, mixed = ans.get(f"soort{n}", {}), ans.get(f"gemengd{n}", {})
        out.append((kind.get("choice"), kind.get("confidence", 0) >= SURE,
                    mixed.get("probability", 0) >= 0.5))
    return out


def month_report(stories, articles):
    m = collections.Counter()
    kinds = collections.Counter()
    with_kind = collections.Counter()
    for s in stories:
        ai, final = s["metadata"]["original_speech_text"], s["text"]
        f = edit_fraction(ai.split(), final.split())
        m["stories"] += 1
        if f > EDITED_MAX:
            m["rewritten"] += 1
            continue
        if ai.split() == final.split():
            continue
        article = (s["metadata"].get("generation") or {}).get("article") or articles.get(str(s["id"]))
        if not article:
            m["no_article"] += 1
            continue
        result = label(article[:8000], ai, final)
        if result is None:
            m["too_many_changes"] += 1
            continue
        seen = set()
        for kind, sure, mixed in result:
            m["changes"] += 1
            key = "gemengd" if mixed else kind if sure else "onzeker"
            kinds[key] += 1
            seen.add(key)
        with_kind.update(seen)
        m["labelled"] += 1
    return {**m, "kinds": dict(kinds), "stories_with_kind": dict(with_kind)}


def write_table(report):
    """The README table: per month the share of each kind among the labelled changes."""
    kinds = [*CODEBOOK["kinds"], "gemengd", "onzeker"]
    head = ["Month", "Stories", "Rewritten", "Changes", *kinds]
    rows = ["| " + " | ".join(head) + " |", "|" + " --- |" * len(head)]
    for month, r in sorted(report.items(), reverse=True):
        n = r.get("changes", 0) or 1
        pct = [f"{100 * r['kinds'].get(k, 0) / n:.0f}%" for k in kinds]
        rows.append(f"| {month} | {r['stories']} | {100 * r.get('rewritten', 0) / r['stories']:.0f}% | "
                    f"{r.get('changes', 0)} | " + " | ".join(pct) + " |")
    readme = open("README.md").read()
    start, end = readme.index("<!-- BEGIN:REPORT -->"), readme.index("<!-- END:REPORT -->")
    table = "\n".join(rows)
    open("README.md", "w").write(f"{readme[:start]}<!-- BEGIN:REPORT -->\n{table}\n{readme[end:]}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("stories")
    p.add_argument("--articles", help="{story_id: article} for stories without metadata.generation")
    p.add_argument("--since", help="first month to (re)compute, YYYY-MM; default three months ago")
    args = p.parse_args()
    today = dt.date.today()
    y, m = divmod(today.year * 12 + today.month - 4, 12)  # the three months before this one
    since = args.since or f"{y}-{m + 1:02d}"
    articles = json.load(open(args.articles)) if args.articles else {}
    months = collections.defaultdict(list)
    for s in json.load(open(args.stories)):
        md = s.get("metadata") or {}
        if (s["status"] == "expired" and not s["deleted_at"] and md.get("original_speech_text")
                and s.get("text") and s["created_at"][:7] >= since):
            months[s["created_at"][:7]].append(s)
    report = json.load(open("report.json")) if os.path.exists("report.json") else {}
    for month in sorted(months):
        new = {"codebook": CODEBOOK["version"], **month_report(months[month], articles)}
        print(month, new["stories"], "stories", new.get("changes", 0), "changes")
        old = report.get(month)
        # Without the backlog articles a rerun labels fewer stories; keep the better month.
        if old and old["codebook"] == new["codebook"] and old.get("labelled", 0) > new.get("labelled", 0):
            continue
        report[month] = new
        json.dump(dict(sorted(report.items())), open("report.json", "w"), indent=1)
    write_table(report)


if __name__ == "__main__":
    main()
