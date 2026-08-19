# AI Collaboration Note

## Did You Use AI?

Yes, heavily — for profiling the data, for pressure-testing the analysis plan, and
for drafting the script and figures.

## How You Used It

Profiling before building. I had it read the domain packet and the CSV together
and list what was structurally wrong before any analysis code existed. That
surfaced the duplicate row, the demo-account spike, the `product` / `Product`
casing split, and the one that mattered most — that 08-07 is missing rows
entirely rather than having missing values, so denominators shift silently.

Enumerating the Q2 candidates rather than jumping at one. Instead of asking
"which metric should they trust least," I had it build the case for every column
that could plausibly win and give me the evidence for each: `median_confidence`
(ρ = 0.86 against user rating through 08-06, then inverts), `flagged_for_review`
(ρ = -0.63, stable, but ambiguous by construction), `avg_minutes_saved`
(ρ = -0.25, and the packet already calls it an estimate, so naming it would be
repeating the packet back with no evidence). Seeing all three side by side is what
made the choice a comparison instead of a guess — and it eliminated minutes saved
on the grounds that there was nothing in the data to indict it with.

Drafting, then correcting. Two fixes went back. The duplicate was originally
caught by matching the string `duplicate export row` in the notes column, which
only works because this export happens to be labelled; it now dedupes structurally
across all non-note fields. And the Q2 scatter first highlighted all four 08-07
rows when only Reply draft / queue is anomalous — three of those rows are
unremarkable, and the annotation arrow was pointing at the wrong one.

## One Prompt, Workflow, Or Moment That Helped

Asking it to kill the obvious angle before I built on it. "Did the 08-04 prompt
change help or hurt" looks like the interesting question in this packet. Checked
first: pre/post acceptance moves .773 → .782 on Lead summary and .768 → .770 on
Reply draft. That is noise on roughly 200 sessions, and the only workflow that
moves at all moves the wrong way (.667 → .657 on Feedback clustering). Ruling it
out in five minutes is why this submission answers two questions it can actually
support instead of one it would have had to walk back.

## One Thing You Verified Or Decided Yourself

The Q2 answer was a fork and I picked the branch. Confidence and
`flagged_for_review` are both defensible, and they fail differently. Flags are
ambiguous by construction — the packet says they move with review policy, output
quality, or user caution, and the cross-section confirms it: within Reply draft,
`queue` flags more than `manual` (.175 vs .129) while beating it on both
acceptance and rating. Confidence is not ambiguous at all, which is the problem.

I went with confidence because a metric that announces its own ambiguity is
already discounted by anyone reading it, and a metric that looks clean until the
day it matters is not. Flags would have been the more contrarian pick and I
considered it seriously; I decided the failure mode worth flagging was the one the
team would not see coming.
