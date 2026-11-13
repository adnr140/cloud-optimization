#!/usr/bin/env python3
"""burst_analysis.py — read a burst_study.sh session, estimate the burst parameters, draw the timeline.
Usage: python3 scripts/burst_analysis.py results/burst/session_<date>
Phases: deplete (long load after an idle charge) gives the burst level, the base level and the credit
stock; recover_<idle> probes give the credits regained after <idle> s of rest (recharge rate).
Speed unit: "full-speed vCPU". u0 = fastest unit seen anywhere (one stream alone at full speed);
a unit that took d seconds ran at speed u0/d; the speed of a VM at time t = sum over its streams.
(e2-standard-2 with 2 streams should give ~1.25: 1 physical core + its hyperthread, our model's c.)
Outputs: SESSION/burst_params.json, SESSION/burst_summary.md, results/fig_burst_timeline.png"""
import csv, json, os, statistics as st, sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S = sys.argv[1]
runs, stats = defaultdict(list), defaultdict(list)
for r in csv.DictReader(open(os.path.join(S, "burst_raw.csv"))):
    key = (r["phase"], r["vm"])
    if r["kind"] == "run":
        runs[key].append((int(r["a"]), float(r["b"]), float(r["c"])))
    elif r["kind"] == "stat":
        stats[key].append((float(r["a"]), float(r["b"]), float(r["c"])))
u0 = min(e - b for v in runs.values() for _, b, e in v)


def series(key, step=1.0):
    """speed(t) sampled every step s from the phase start, and steal fraction per sample."""
    rs = runs[key]
    t0 = min(b for _, b, _ in rs)
    t1 = max(e for _, _, e in rs)
    out, t = [], t0
    while t < t1:
        sp = sum(u0 / (e - b) for _, b, e in rs if b <= t < e)
        out.append((t - t0, sp))
        t += step
    steal = []
    ss = sorted(stats[key])
    for (ta, sa, ca), (tb, sb, cb) in zip(ss, ss[1:]):
        if cb > ca:
            steal.append((ta - t0, 100 * (sb - sa) / (cb - ca)))
    return out, steal


def smooth(xs, w=5):
    return [st.mean(xs[max(0, i - w + 1):i + 1]) for i in range(len(xs))]


def burst_metrics(sp, base=None):
    """initial / final speed, how long the burst held (s), credits = work done above the base speed.
    base: the VM's own speed once depleted (from the depletion phase); a probe may end before it drops."""
    lv = smooth([s for _, s in sp])
    first = st.mean(lv[2:22]) if len(lv) > 25 else st.mean(lv)
    last = st.mean(lv[-60:]) if len(lv) > 90 else st.mean(lv[-10:])
    ref = base if base is not None else last
    dropped = first - ref > 0.15 * first
    mid = (first + ref) / 2
    t_drop = next((sp[i][0] for i in range(len(lv)) if lv[i] < mid), None) if dropped else None
    credits = None
    if dropped:
        end = t_drop if t_drop is not None else sp[-1][0]
        credits = sum(max(0.0, s - ref) for t, s in sp if t <= end + 30)
    return {"initial_speed": round(first, 3), "final_speed": round(last, 3), "burst_s": t_drop,
            "held_whole_probe": dropped and t_drop is None, "credits_vcpu_s": round(credits, 1) if credits is not None else None}


def order(key):
    ph = key[0]
    return (0 if ph == "deplete" else int(ph.split("_")[1]), key[1])


params = {"u0_s": round(u0, 4), "phases": {}}
base = {}
for key in sorted(runs, key=order):
    sp, _ = series(key)
    m = burst_metrics(sp, base.get(key[1]) if key[0] != "deplete" else None)
    if key[0] == "deplete":
        base[key[1]] = m["final_speed"]
    params["phases"][f"{key[0]}|{key[1]}"] = {"streams": len({k for k, _, _ in runs[key]}), "duration_s": round(sp[-1][0]), **m}
json.dump(params, open(os.path.join(S, "burst_params.json"), "w"), indent=1)

lines = [f"# Burst : session {os.path.basename(S)}", "", f"Unité : la plus rapide vue = {u0:.3f} s (= vitesse 1).", "",
         "| phase | VM | flux | durée (s) | vitesse au début | vitesse à la fin | burst tenu (s) | crédits (vCPU·s au-dessus du régime de base) |",
         "|---|---|---:|---:|---:|---:|---:|---:|"]
for k, v in params["phases"].items():
    ph, vm = k.split("|")
    lines.append(f"| {ph} | {vm} | {v['streams']} | {v['duration_s']} | {v['initial_speed']:.2f} | {v['final_speed']:.2f} | "
                 f"{v['burst_s'] if v['burst_s'] is not None else ('toute la sonde' if v['held_whole_probe'] else 'pas de burst')} | "
                 f"{('≥ ' if v['held_whole_probe'] else '') + str(v['credits_vcpu_s']) if v['credits_vcpu_s'] is not None else '—'} |")
open(os.path.join(S, "burst_summary.md"), "w").write("\n".join(lines) + "\n")
print("\n".join(lines))

import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
BLUE, ORANGE, AQUA, INK2, GRID = "#2a78d6", "#eb6834", "#1baf7a", "#52514e", "#e6e5e0"
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
                     "grid.color": GRID, "axes.axisbelow": True, "legend.frameon": False})
fig, (a, b) = plt.subplots(2, 1, figsize=(10, 6), sharex=True, gridspec_kw={"height_ratios": [3, 1.4]})
for vm, lab, col in [("cloudopt-vm1", "e2-standard-2, 2 vCPU occupés (témoin)", BLUE),
                     ("cloudopt-vm2", "e2-medium, 2 vCPU occupés", ORANGE), ("cloudopt-vm3", "e2-medium, 1 vCPU occupé", AQUA)]:
    if ("deplete", vm) not in runs:
        continue
    sp, steal = series(("deplete", vm))
    a.plot([t for t, _ in sp], smooth([s for _, s in sp]), color=col, lw=2, label=lab)
    b.plot([t for t, _ in steal], smooth([s for _, s in steal]), color=col, lw=1.5)
a.set_ylabel("vitesse (vCPU à pleine vitesse)"); a.set_ylim(bottom=0)
a.set_title("Après une pause, l'e2-medium tourne à pleine vitesse, puis retombe à son régime de base")
a.legend(fontsize=8.5, loc="upper right")
b.set_ylabel("vol de CPU (%)"); b.set_xlabel("secondes de charge continue"); b.set_ylim(bottom=0)
fig.tight_layout(); fig.savefig(os.path.join(ROOT, "results/fig_burst_timeline.png"), dpi=150)
fig.savefig(os.path.join(S, "fig_burst_timeline.png"), dpi=150)
print("written: results/fig_burst_timeline.png")
