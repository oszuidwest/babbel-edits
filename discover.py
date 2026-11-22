#!/usr/bin/env python3
"""Find the kinds of edits once: a text model describes the edits in a sample, then groups them.

Writes private/discovery.json (descriptions with story ids, never committed) and prints the
proposed kinds, which become codebook.json after review.
"""

import collections
import difflib
import json
import os
import random
import sys
import urllib.error
import urllib.request

MODEL = "gpt-6.2-sol"
SAMPLE = 60
BATCH = 6


def call(instructions, text):
    # The json_object format needs the word JSON in the input itself.
    body = {"model": MODEL, "instructions": instructions, "input": "Answer in JSON.\n\n" + text,
            "max_output_tokens": 16000, "text": {"format": {"type": "json_object"}}}
    req = urllib.request.Request(
        "https://api.openai.com/v1/responses", data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}",
                 "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            res = json.load(r)
    except urllib.error.HTTPError as e:
        raise RuntimeError(e.read().decode()[:500]) from e
    if res.get("status") != "completed":
        raise RuntimeError(f"response {res.get('status')}: {res.get('incomplete_details')}")
    return json.loads("".join(c.get("text", "") for o in res["output"] if o["type"] == "message"
                              for c in o["content"]))


def diff(a, b):
    a, b = a.split(), b.split()
    out = []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        out.append(" ".join(a[i1:i2]) if op == "equal" else
                   f"[-{' '.join(a[i1:i2])}-]{{+{' '.join(b[j1:j2])}+}}")
    return " ".join(out)


DESCRIBE = (
    "You get Dutch local news stories: the web article, the radio text an AI wrote from it "
    "(about 65 words, read aloud by a synthetic voice), the text the editors broadcast, and a "
    "word diff. List every separate change the editors made. For each change give: before "
    "(exact AI words, or empty), after (exact broadcast words, or empty), what (a short, "
    "general description of the KIND of change in English, without the story's content, e.g. "
    "'moved the place name out of the opening'), why (the most likely reason, or 'unclear'), "
    "and source: 'article' if the new content is in the article, 'not in article', or 'n/a'. "
    'Answer in JSON: {"stories": [{"id": "...", "changes": [{"before": "", "after": "", '
    '"what": "", "why": "", "source": ""}]}]}'
)
GROUP = (
    "Below are short descriptions of edits Dutch radio editors made to AI-written read-aloud "
    "news texts, one per line with an id. Group them into at most 10 kinds of change. Kinds "
    "must be defined by what can be observed in the before/after text (not by guessed intent), "
    "must not overlap, and must be easy to tell apart. For each kind give: name (one Dutch "
    "word, lowercase), description (one Dutch sentence an editor understands, with the "
    "observable criterion), prompt (true if a rule in the AI prompt could prevent it), and the "
    "ids it covers. Put what fits nowhere in 'anders'. "
    'Answer in JSON: {"kinds": [{"name": "", "description": "", "prompt": true, "ids": []}]}'
)


def main():
    stories = json.load(open(sys.argv[1]))
    articles = json.load(open(sys.argv[2]))
    done = [s for s in stories if s["status"] == "expired" and not s["deleted_at"]
            and (s.get("metadata") or {}).get("original_speech_text") and s.get("text")
            and str(s["id"]) in articles
            and s["metadata"]["original_speech_text"].split() != s["text"].split()]
    months = collections.defaultdict(list)
    for s in done:
        months[s["created_at"][:7]].append(s)
    rng = random.Random(1)
    per = -(-SAMPLE // len(months))
    sample = [s for m in sorted(months) for s in rng.sample(months[m], min(per, len(months[m])))]
    sample = rng.sample(sample, SAMPLE)
    out = []
    for i in range(0, len(sample), BATCH):
        text = "\n\n".join(
            f"ITEM {s['id']}\nARTICLE: {articles[str(s['id'])][:8000]}\n"
            f"AI: {s['metadata']['original_speech_text']}\nBROADCAST: {s['text']}\n"
            f"DIFF: {diff(s['metadata']['original_speech_text'], s['text'])}"
            for s in sample[i:i + BATCH])
        out += call(DESCRIBE, text)["stories"]
        print(f"described {len(out)} stories", file=sys.stderr)
    lines = [f"{s['id']}.{n} {c['what']} (why: {c['why']}; source: {c['source']})"
             for s in out for n, c in enumerate(s["changes"])]
    kinds = call(GROUP, "\n".join(lines))
    json.dump({"sample": [s["id"] for s in sample], "stories": out, "kinds": kinds},
              open("private/discovery.json", "w"), ensure_ascii=False, indent=1)
    for k in kinds["kinds"]:
        print(f"{k['name']:14} {len(k['ids']):4}  prompt={k['prompt']}  {k['description']}")


if __name__ == "__main__":
    main()
