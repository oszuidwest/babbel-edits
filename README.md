# babbel-edits

What kinds of changes do the editors make to the AI-written radio texts in
[Babbel](https://github.com/oszuidwest/zwfm-babbel)? This repo sorts them per month. The
weekly accuracy numbers stay in [babbel-analyse](https://github.com/oszuidwest/babbel-analyse).

Only totals are published here. Story texts, the parts editors removed and the articles stay
out of this repo, because removed text can hold names or claims that were deliberately not
broadcast.

## How it works

`edits.py` takes every story that finished airing and was not deleted. Stories with more than
40% of their words changed count as rewritten and get no kinds. For the others, the word diff
between the AI text and the broadcast text is cut into changes. Nearby edits in one sentence
merge into one change; a change can still span sentences when the editors rewrote across them.

Each story then goes to the [OpenAI Decisions API](https://developers.openai.com/api/docs/guides/decisions)
once, with the article, both texts and the list of changes. For every change the model picks
one kind from `codebook.json` and gives the probability that the change mixes several kinds. A
change counts as "gemengd" when that probability is at least 0.5, otherwise as "onzeker" when
the model's confidence in the kind is under 0.6.

The kinds come from `discover.py`. A text model described the changes in 60 stories sampled
across the months and grouped them, and the owner approved the list.

One editor then checked other stories against the model. The goal, set beforehand: in stories
where the editor does not see the model's answers, the editor agrees with at least 80% of the
changes the model counts, and at most a quarter of the changes are onzeker. In the first round
10 of the 40 stories were checked that way, and 6 of the 11 counted changes matched (55%). After
the descriptions were sharpened, a second round of 25 stories, all checked that way, matched 31
of 43 (72%), with 14% onzeker. That missed the goal, but the owner judged it good enough and
stopped the checks. The descriptions were then sharpened once more with the editor's choices
from the second round; that version was not checked again. Read the table as a rough picture of
which kinds of changes are common, not as an exact count. The model also used to check whether
the AI text contradicted the article; that check has been dropped.

## Kinds

| Kind | Meaning |
| --- | --- |
| schrapping | Something is removed without anything taking its place, such as a word like "waarschijnlijk" or a place name. |
| aanvulling | Information is added, or a reference or time becomes more precise. |
| inhoud | A statement is replaced by a different one, such as another outcome or a number that changes by more than rounding. |
| ordening | The same information moves, for example a place name out of the opening. |
| tijd | For the same event, the tense changes, or a time is put another way without becoming more precise, such as a date that becomes "dit jaar". |
| formulering | Other words or grammar, with the same facts in the same place. |
| notatie | Only the writing changes: spelling, digits, punctuation, units, abbreviations, or rounding so a number sounds better. |
| anders | Does not fit any of the other kinds. |

## Results

Share of each kind among the labelled changes, per month. Rewritten stories are not in the
changes.

<!-- BEGIN:REPORT -->
| Month | Stories | Rewritten | Changes | schrapping | aanvulling | inhoud | ordening | tijd | formulering | notatie | anders | gemengd | onzeker |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-11 | 148 | 14% | 196 | 7% | 29% | 10% | 0% | 7% | 6% | 5% | 0% | 15% | 22% |
| 2026-10 | 221 | 14% | 241 | 11% | 27% | 7% | 0% | 7% | 8% | 3% | 0% | 8% | 28% |
| 2026-09 | 215 | 14% | 213 | 13% | 25% | 8% | 0% | 8% | 7% | 5% | 0% | 9% | 25% |
| 2026-08 | 171 | 12% | 111 | 12% | 29% | 7% | 2% | 1% | 7% | 1% | 0% | 14% | 27% |
| 2026-07 | 193 | 17% | 157 | 13% | 25% | 6% | 1% | 8% | 14% | 2% | 0% | 10% | 19% |
| 2026-06 | 206 | 10% | 198 | 13% | 22% | 13% | 1% | 8% | 10% | 3% | 0% | 8% | 24% |
| 2026-05 | 215 | 10% | 199 | 16% | 23% | 11% | 0% | 7% | 11% | 3% | 0% | 7% | 24% |
| 2026-04 | 217 | 27% | 171 | 16% | 16% | 6% | 2% | 4% | 12% | 5% | 0% | 13% | 27% |
| 2026-03 | 228 | 90% | 52 | 19% | 4% | 8% | 2% | 2% | 4% | 6% | 0% | 29% | 27% |
| 2026-02 | 181 | 53% | 244 | 23% | 5% | 5% | 5% | 2% | 4% | 9% | 0% | 21% | 25% |
| 2026-01 | 176 | 31% | 351 | 22% | 6% | 3% | 7% | 1% | 4% | 8% | 0% | 24% | 24% |
<!-- END:REPORT -->

## Running

```sh
export BABBEL_USERNAME=... BABBEL_PASSWORD=... OPENAI_API_KEY=...
python3 ../babbel-analyse/fetch_all.py   # writes stories.json
python3 edits.py stories.json            # the three months before this one, and this one
python3 edits.py stories.json --since 2026-01 --articles private/articles.json
```

Stories made before the plugin stored the article in `metadata.generation` need `--articles`,
a JSON file of `{story_id: article}` rebuilt from WordPress revisions. Keep it in `private/`,
which git ignores. A rerun without it keeps the month that had more labelled stories. Labelling
the 1010 stories since January costs about 20 cents.

The workflow runs on the second of every month and commits `report.json` and the table above.

## Secrets

- `BABBEL_USERNAME`, `BABBEL_PASSWORD`
- `OPENAI_API_KEY`
