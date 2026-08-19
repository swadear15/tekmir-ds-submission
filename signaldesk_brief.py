"""
SignalDesk two-question brief.

Answers two of the questions the team asked:

    Q1. Which workflow seems most useful right now?
    Q2. Which metric should they trust least?

    python signaldesk_brief.py sample-data/product_usage_events.csv

Prints a brief and writes two figures to figures/.
Requires pandas, scipy, matplotlib.
"""

import argparse
import os
import sys

import matplotlib
matplotlib.use("Agg")  # headless: reviewers should not need a display
import matplotlib.pyplot as plt
import pandas as pd
from scipy.stats import spearmanr

# The day a review policy changed mid-day. Deliberately NOT excluded --
# it is the Q2 finding, not contamination.
POLICY_CHANGE = "2026-08-07"

INK = "#1b1b1b"
MUTED = "#8a8a8a"
ALARM = "#c0392b"
CALM = "#2c6e9b"
FADE = "#c8d3da"
RULE = "-" * 76


# --------------------------------------------------------------------------
# cleaning
# --------------------------------------------------------------------------
def clean(path):
    """Load and clean. Returns (kept, dropped) where dropped carries a reason.

    Two rows leave. Everything else stays, including the policy-change day.
    """
    df = pd.read_csv(path)
    df["notes"] = df["notes"].fillna("")

    # `product` and `Product` are one team; the export disagrees with itself.
    df["team"] = df["team"].str.strip().str.title()
    df["workflow"] = df["workflow"].str.strip()
    df["source"] = df["source"].str.strip()

    reasons = pd.Series("", index=df.index)

    # Structural duplicate: identical on every field but the free-text note.
    # Detected structurally rather than by matching the note string, because
    # the next duplicated export will not arrive helpfully labelled.
    key = [c for c in df.columns if c != "notes"]
    reasons[df.duplicated(subset=key, keep="first")] = "duplicate of an earlier row"

    demo = df["notes"].str.contains("demo account", case=False) & (reasons == "")
    reasons[demo] = "demo-account traffic, not real usage"

    dropped = df[reasons != ""].copy()
    dropped["reason"] = reasons[reasons != ""]
    kept = df[reasons == ""].copy()

    # Rates come from summed counts everywhere downstream, never from a mean
    # of daily rates -- that would weight a 5-session day like a 70-session one.
    kept["accept_rate"] = kept["accepted_output"] / kept["completed"]
    kept["flag_rate"] = kept["flagged_for_review"] / kept["completed"]
    return kept, dropped


def wmean(g, col, weight="sessions"):
    """Session-weighted mean. Nulls leave both numerator and denominator."""
    ok = g[col].notna()
    w = g.loc[ok, weight]
    return (g.loc[ok, col] * w).sum() / w.sum() if w.sum() else float("nan")


def coverage_gaps(kept):
    """Combos present on day one and absent later.

    A missing row is not a missing value: it changes a denominator silently.
    """
    dates = sorted(kept["date"].unique())
    base = set(
        kept[kept["date"] == dates[0]][["team", "workflow", "source"]]
        .itertuples(index=False, name=None)
    )
    out = []
    for d in dates[1:]:
        seen = set(
            kept[kept["date"] == d][["team", "workflow", "source"]]
            .itertuples(index=False, name=None)
        )
        out += [(d, *c) for c in sorted(base - seen)]
    return out


# --------------------------------------------------------------------------
# Q2 -- which metric to trust least
# --------------------------------------------------------------------------
def confidence_case(kept):
    """The case against median_confidence.

    The argument is not that confidence is noise. It is that confidence is
    reliable enough to become load-bearing, then inverts without warning.
    """
    both = kept.dropna(subset=["median_confidence", "user_rating"])
    before = both[both["date"] < POLICY_CHANGE]

    q = kept[(kept["workflow"] == "Reply draft") & (kept["source"] == "queue")]
    q = q.sort_values("date")
    break_row = q[q["date"] == POLICY_CHANGE].iloc[0]
    prior = q[q["date"] < POLICY_CHANGE]

    return {
        "rho_all": spearmanr(both["median_confidence"], both["user_rating"])[0],
        "rho_before": spearmanr(before["median_confidence"], before["user_rating"])[0],
        "n_all": len(both),
        "series": q,
        "break_row": break_row,
        "d_conf": break_row["median_confidence"] - prior["median_confidence"].median(),
        "d_accept": break_row["accept_rate"] - prior["accept_rate"].median(),
        "d_rating": break_row["user_rating"] - prior["user_rating"].median(),
        "is_week_max": break_row["median_confidence"] >= q["median_confidence"].max(),
    }


# --------------------------------------------------------------------------
# Q1 -- which workflow is most useful
# --------------------------------------------------------------------------
DEFINITIONS = [
    "Acceptance rate",
    "Minutes saved per session",
    "Gross minutes saved",
    "Realized minutes saved",
]


def usefulness(kept):
    """Four defensible readings of "useful". They do not all agree."""

    def row(x):
        return pd.Series(
            {
                "sessions": x["sessions"].sum(),
                "Acceptance rate": x["accepted_output"].sum() / x["completed"].sum(),
                "Minutes saved per session": wmean(x, "avg_minutes_saved"),
                "Gross minutes saved": (x["avg_minutes_saved"] * x["sessions"]).sum(),
                # Realized counts only outputs a human kept. This is the
                # definition that flips the ranking.
                "Realized minutes saved": (
                    x["avg_minutes_saved"] * x["accepted_output"]
                ).sum(),
            }
        )

    return kept.groupby("workflow").apply(row, include_groups=False)


# --------------------------------------------------------------------------
# figures
# --------------------------------------------------------------------------
def style(ax):
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(MUTED)
    ax.tick_params(colors=MUTED, labelsize=9)
    ax.title.set_color(INK)


def fig_q1(u, outdir):
    """Four readings of usefulness, each scaled to its own leader."""
    workflows = list(u.index)
    fig, axes = plt.subplots(1, 4, figsize=(13, 3.6), sharey=True)

    for ax, m in zip(axes, DEFINITIONS):
        scaled = u[m] / u[m].max()
        colors = [CALM if u.loc[w, m] == u[m].max() else FADE for w in workflows]
        ax.barh(workflows, scaled, color=colors, height=0.55)
        for i, w in enumerate(workflows):
            raw = u.loc[w, m]
            label = (f"{raw:.2f}" if raw < 1 else
                     f"{raw:.1f}" if raw < 100 else f"{raw:,.0f}")
            ax.text(scaled[w] + 0.03, i, label, va="center", fontsize=9, color=INK)
        ax.set_title(m, fontsize=10, pad=10)
        ax.set_xlim(0, 1.35)
        ax.set_xticks([])
        style(ax)

    fig.suptitle(
        "Q1  \u2014  'Useful' has four honest definitions. Lead summary wins three.",
        fontsize=12, color=INK, y=1.04, x=0.02, ha="left",
    )
    fig.text(
        0.02, -0.10,
        "Bars scaled to the leader in each panel. Realized minutes counts only accepted "
        "outputs \u2014 Feedback clustering's per-session\nadvantage disappears there, because "
        "its acceptance rate is the worst of the three.",
        fontsize=8.5, color=MUTED, ha="left",
    )
    fig.tight_layout()
    path = os.path.join(outdir, "q1_usefulness.png")
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


def fig_q2(case, kept, outdir):
    """Left: confidence usually works. Right: the one day it does not."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.4))
    br = case["break_row"]

    # -- left: the correlation that makes confidence trustworthy-looking ----
    both = kept.dropna(subset=["median_confidence", "user_rating"])
    is_break = (
        (both["date"] == POLICY_CHANGE)
        & (both["workflow"] == "Reply draft")
        & (both["source"] == "queue")
    )
    rest, point = both[~is_break], both[is_break]

    ax1.scatter(rest["median_confidence"], rest["user_rating"],
                s=34, color=CALM, alpha=0.75, label="every other row", zorder=3)
    ax1.scatter(point["median_confidence"], point["user_rating"], s=110,
                color=ALARM, marker="X", label="Reply draft / queue, Aug 7", zorder=4)
    ax1.set_xlabel("median_confidence", fontsize=9, color=MUTED)
    ax1.set_ylabel("user_rating", fontsize=9, color=MUTED)
    ax1.set_title(
        f"Confidence tracks quality well \u2014 \u03c1 = {case['rho_before']:.2f} through Aug 6",
        fontsize=10.5, pad=14,
    )
    ax1.legend(frameon=False, fontsize=8.5, loc="lower left")
    style(ax1)
    ax1.annotate(
        "highest confidence\nof the week,\nlowest rating",
        xy=(float(br["median_confidence"]), float(br["user_rating"])),
        xytext=(-96, 30), textcoords="offset points", fontsize=8.5, color=ALARM,
        arrowprops=dict(arrowstyle="->", color=ALARM, lw=1),
    )

    # -- right: the divergence, on the highest-volume workflow -------------
    s = case["series"]
    days = [str(d)[5:] for d in s["date"]]
    ax2.plot(days, s["median_confidence"], marker="o", ms=5, color=CALM, lw=2,
             label="median_confidence")
    ax2.plot(days, s["accept_rate"], marker="o", ms=5, color=ALARM, lw=2,
             label="acceptance (accepted / completed)")
    ax2.plot(days, s["user_rating"] / 5, marker="o", ms=4, color=MUTED, lw=1.4,
             ls="--", label="user_rating (\u00f7 5)")
    ax2.axvline(len(days) - 1, color=MUTED, lw=1, ls=":", zorder=0)
    ax2.set_ylim(0, 1.05)
    ax2.set_title("Reply draft / queue \u2014 the day it inverts", fontsize=10.5, pad=14)
    ax2.legend(frameon=False, fontsize=8.5, loc="lower left")
    style(ax2)
    ax2.annotate(
        f"confidence {case['d_conf']:+.2f}\nacceptance {case['d_accept']:+.2f}\n"
        f"rating {case['d_rating']:+.1f}",
        xy=(len(days) - 1, 0.47), xytext=(-118, 6), textcoords="offset points",
        fontsize=8.5, color=ALARM,
        arrowprops=dict(arrowstyle="->", color=ALARM, lw=1),
    )

    fig.suptitle(
        "Q2  \u2014  Trust median_confidence least. Not because it is noisy, "
        "because it is reliable until it is not.",
        fontsize=12, color=INK, y=1.06, x=0.02, ha="left",
    )
    fig.text(
        0.02, -0.06,
        "Aug 7 note: \"review policy changed mid-day\". Both quality proxies failed at once "
        "\u2014 confidence inverted, and the flag count\nmoved for a policy reason rather than "
        "a model reason. There was no fallback signal that day.",
        fontsize=8.5, color=MUTED, ha="left",
    )
    fig.tight_layout()
    path = os.path.join(outdir, "q2_confidence.png")
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


# --------------------------------------------------------------------------
# the brief
# --------------------------------------------------------------------------
def brief(path, outdir="figures"):
    kept, dropped = clean(path)
    os.makedirs(outdir, exist_ok=True)

    print(RULE)
    print("SIGNALDESK BRIEF \u2014 two questions")
    print(RULE)

    print(f"\nCLEANING  ({len(kept)} of {len(kept) + len(dropped)} rows used)\n")
    for _, r in dropped.iterrows():
        print(f"  dropped  {r['date']}  {r['workflow']:<20} {r['source']:<11} "
              f"{int(r['sessions']):>4} sessions  <- {r['reason']}")
    print("  team casing normalized (`product` -> `Product`)")
    for d, team, wf, src in coverage_gaps(kept):
        print(f"  absent   {d}  {wf:<20} {src:<11} no usable {team} row "
              f"<- denominator shifts, no raw day-over-day totals quoted")
    print("  Aug 7 is KEPT. It is the Q2 finding, not contamination.")

    # ---- Q1 ----
    u = usefulness(kept)
    print("\n\nQ1  WHICH WORKFLOW SEEMS MOST USEFUL\n")
    print(f"  {'workflow':<21} {'sess':>5} {'accept':>7} {'min/sess':>9} "
          f"{'gross min':>10} {'realized':>9}")
    for w, r in u.iterrows():
        print(f"  {w:<21} {int(r['sessions']):>5} {r['Acceptance rate']:>7.2f} "
              f"{r['Minutes saved per session']:>9.1f} "
              f"{r['Gross minutes saved']:>10,.0f} "
              f"{r['Realized minutes saved']:>9,.0f}")

    wins = {w: sum(u.loc[w, m] == u[m].max() for m in DEFINITIONS) for w in u.index}
    best = max(wins, key=wins.get)
    print(f"\n  ANSWER: {best}. It leads {wins[best]} of the 4 readings of 'useful'.")
    print("  Feedback clustering leads on minutes saved per session (13.1), which is")
    print("  the number a demo would show. It is a bet, not a result: worst acceptance")
    print("  of the three, worst completion rate, 207 sessions all week. Counting only")
    print("  minutes on outputs a human kept, it finishes last.")

    # ---- Q2 ----
    c = confidence_case(kept)
    b = c["break_row"]
    print("\n\nQ2  WHICH METRIC SHOULD THEY TRUST LEAST\n")
    print("  ANSWER: median_confidence.")
    print("\n  The case is not that it is noise. Across the clean panel it tracks")
    print(f"  user_rating at rho = {c['rho_all']:.2f} (n = {c['n_all']}), and "
          f"rho = {c['rho_before']:.2f} through Aug 6.")
    print("  It is good enough to become load-bearing in a rollout decision.")
    print(f"\n  Then on {b['date']}, Reply draft / queue \u2014 the highest-volume workflow:")
    print(f"    median_confidence  {c['d_conf']:+.2f}   (to {b['median_confidence']:.2f}, "
          f"its highest of the week)")
    print(f"    acceptance         {c['d_accept']:+.2f}   (to {b['accept_rate']:.2f})")
    print(f"    user_rating        {c['d_rating']:+.1f}   (to {b['user_rating']:.1f})")
    print("\n  It moved the wrong way at the one moment a decision depended on it, and")
    print("  a high-confidence bad day looks identical to a high-confidence good day")
    print("  while you are inside it.")
    print("\n  Runner-up: flagged_for_review is ambiguous by definition \u2014 but it says so")
    print("  up front, so it is already discounted. Confidence is not. Note that flags")
    print("  moved on Aug 7 for a policy reason too, so the obvious fallback signal was")
    print("  unavailable exactly when it was needed.")

    print(f"\n\n  figures: {fig_q1(u, outdir)}, {fig_q2(c, kept, outdir)}")
    print(RULE)


def main():
    p = argparse.ArgumentParser(description="SignalDesk two-question brief")
    p.add_argument("csv", nargs="?", default="sample-data/product_usage_events.csv")
    p.add_argument("--outdir", default="figures")
    a = p.parse_args()
    try:
        brief(a.csv, a.outdir)
    except FileNotFoundError:
        sys.exit(f"No such file: {a.csv}")


if __name__ == "__main__":
    main()
