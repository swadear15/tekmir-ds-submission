# Submission README

## Track Chosen

Track A — Fictional Domain Packet (SignalDesk).

## What I Built

Cleans the export, then answers two of the team's questions: which workflow is
most useful, and which metric to trust least.

```
python signaldesk_brief.py sample-data/product_usage_events.csv
```

**Q1: Lead summary** — "useful" has four honest definitions; it leads three.
**Q2: `median_confidence`** — not because it is noisy, because it isn't.

## Who It Is For

The teammate deciding whether to roll these workflows out: one workflow to back,
one number to stop quoting.

## Data Or Source Used

`sample-data/product_usage_events.csv` from this repo. 41 fictional rows, 08-01
to 08-07, one per date x team x workflow x source. 39 used.

## Assumptions I Made

- Acceptance is `accepted_output / completed`. A run that never finished was
  never offered to anyone.
- Rates come from summed counts; averaging daily rates would weight a 5-session
  day like a 70-session one. Minutes and confidence are session-weighted, nulls
  excluded from numerator and denominator.
- Minutes saved appears gross and realized (accepted only). The choice decides
  Q1, so both are shown.
- Never aggregated across `source`: `manual` underperforms its sibling
  everywhere, so a workflow average partly measures mix.

## Data Issues Or Caveats I Noticed

- A duplicate row and a demo-account spike, both 08-05 Sales/Lead summary/email,
  leaving no usable email number that day.
- Missing rows, not values, on 08-07. Denominators shift silently.
- `product` vs `Product` casing splits a groupby.
- 08-07 is kept deliberately. Confidence tracks rating at ρ = 0.86 through 08-06,
  then inverts. Flags moved that day for a policy reason too, so both quality
  proxies failed at once.

## What I Would Do Next With More Time

Session-level data to separate the 08-07 policy change from output quality. Every
quality column is a proxy, so sampled human review is the real check.
