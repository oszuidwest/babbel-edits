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
one kind from `codebook.json` and gives two probabilities: that the change mixes several kinds,
and that the AI text contradicted the article there. A change counts as "gemengd" when the
first probability is at least 0.5, otherwise as "onzeker" when the model's confidence in the
kind is under 0.6. "Contradicts article" counts changes with a probability of at least 0.7.
These are the model's proposals, checked against an article that may be incomplete. The
thresholds are provisional.

The kinds come from `discover.py`. A text model described the changes in 60 stories sampled
across the months and grouped them, and the owner approved the list. One editor still has to
check a sample of 40 stories. That check sets the thresholds; until then the numbers are
provisional.

## Kinds

| Kind | Meaning |
| --- | --- |
| schrapping | Something is removed without anything taking its place. |
| aanvulling | Information is added, or a reference becomes more concrete. |
| inhoud | A statement is replaced by a different one, such as another number or outcome. |
| ordening | The same information moves, for example a place name out of the opening. |
| tijd | The tense or the time reference changes, such as a date that becomes "dit jaar". |
| formulering | Other words or grammar, with the same facts in the same place. |
| notatie | Only the writing changes: spelling, digits, punctuation, units. |

## Results

Share of each kind among the labelled changes, per month. Rewritten stories are not in the
changes.

<!-- BEGIN:REPORT -->
| Month | Stories | Rewritten | Changes | schrapping | aanvulling | inhoud | ordening | tijd | formulering | notatie | anders | gemengd | onzeker | Contradicts article |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-11 | 148 | 14% | 196 | 5% | 26% | 12% | 1% | 9% | 12% | 1% | 0% | 15% | 21% | 9 |
| 2026-10 | 221 | 14% | 241 | 10% | 28% | 11% | 0% | 9% | 15% | 1% | 0% | 8% | 18% | 13 |
| 2026-09 | 215 | 14% | 213 | 11% | 26% | 10% | 2% | 8% | 14% | 2% | 0% | 9% | 18% | 7 |
| 2026-08 | 171 | 12% | 111 | 11% | 24% | 11% | 2% | 6% | 12% | 0% | 0% | 14% | 20% | 19 |
| 2026-07 | 193 | 17% | 157 | 13% | 24% | 8% | 1% | 10% | 18% | 1% | 0% | 10% | 15% | 10 |
| 2026-06 | 206 | 10% | 198 | 11% | 20% | 18% | 2% | 11% | 18% | 1% | 0% | 8% | 13% | 15 |
| 2026-05 | 215 | 10% | 199 | 14% | 22% | 10% | 0% | 10% | 20% | 2% | 0% | 7% | 17% | 18 |
| 2026-04 | 217 | 27% | 171 | 14% | 16% | 6% | 2% | 8% | 16% | 4% | 0% | 13% | 21% | 16 |
| 2026-03 | 228 | 90% | 52 | 21% | 6% | 10% | 6% | 2% | 2% | 6% | 0% | 29% | 19% | 7 |
| 2026-02 | 181 | 53% | 244 | 21% | 5% | 4% | 7% | 2% | 9% | 9% | 0% | 21% | 21% | 13 |
| 2026-01 | 176 | 31% | 351 | 21% | 7% | 4% | 6% | 2% | 9% | 8% | 0% | 24% | 18% | 19 |
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
