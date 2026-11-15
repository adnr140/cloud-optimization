#!/usr/bin/env python3
"""session_summary.py — summary of one compare_run.sh session (predicted vs measured makespan).
Usage: python3 scripts/session_summary.py results/project/session_<date>
Measured makespan of a run = last end - first launch (controller clock, SSH included), as makespan.sh.
Predicted = bin/optimizer -method eval with the p_ij measured in the same session."""
import csv, glob, os, re, statistics as st, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S = sys.argv[1]
TASKS = {"A": "data/tasks.csv", "B": "data/tasks_b.csv"}


def measured(run):
    l, e = [], []
    for f in glob.glob(os.path.join(run, "*.meta")):
        kv = dict(x.strip().split("=", 1) for x in open(f) if "=" in x)
        l.append(float(kv["launch_epoch"])); e.append(float(kv["end_epoch"]))
    return max(e) - min(l)


# p_ij of the session; the corrected file (scripts/correct_medium_p.py) when the e2-medium was measured out of burst
PF = next(f for f in (os.path.join(S, "p_matrix_now_corrected.csv"), os.path.join(S, "p_matrix_now.csv")) if os.path.exists(f))


def predicted(name):
    out = subprocess.run([os.path.join(ROOT, "bin/optimizer"), "-method", "eval", "-p", PF,
                          "-vms", os.path.join(S, "vms_now.csv"), "-tasks", os.path.join(ROOT, TASKS[name[0]]),
                          "-alloc", os.path.join(S, "alloc", name + ".csv")], capture_output=True, text=True, cwd=ROOT).stdout
    return float(re.search(r"makespan=([0-9.]+)", out).group(1))


names = ["A_rr", "A_opt", "B_rr", "B_lpt", "B_opt"]
reps = sorted(glob.glob(os.path.join(S, "rep*")))
res = {n: [measured(os.path.join(r, n)) for r in reps if os.path.isdir(os.path.join(r, n))] for n in names}
lines = [f"# Session {os.path.basename(S)} : Round-Robin vs LPT vs opt sur les vraies VMs", "",
         f"{len(reps)} répétitions par allocation, ordre tourné à chaque répétition ; p_ij mesurés dans la même session (`p_matrix_now.csv`).",
         "Makespan mesuré = dernière fin − premier lancement (horloge du contrôleur, SSH compris).", "",
         "| scénario | méthode | prédit (s) | mesuré moyen (s) | min – max (s) | vs Round-Robin (mesuré) |",
         "|---|---|---:|---:|---:|---:|"]
for n in names:
    m = res[n]
    rr = st.mean(res[n[0] + "_rr"])
    gain = "—" if n.endswith("_rr") else f"{100 * (st.mean(m) - rr) / rr:+.0f} %"
    lines.append(f"| {n[0]} | {n[2:]} | {predicted(n):.1f} | {st.mean(m):.1f} | {min(m):.1f} – {max(m):.1f} | {gain} |")
lines += ["", "Mesures brutes (s) : " + " ; ".join(f"{n} = " + ", ".join(f"{x:.1f}" for x in res[n]) for n in names), "",
          f"Plateforme : voir `platform.txt` ; p_ij du jour : `{os.path.basename(PF)}`."]
text = "\n".join(lines) + "\n"
open(os.path.join(S, "summary.md"), "w").write(text)
print(text)

# figure: measured (mean, min-max over the repetitions) vs predicted, per allocation
try:
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except ImportError:
    sys.exit(0)
BLUE, GRAY, INK, INK2, GRID = "#2a78d6", "#9a9890", "#0b0b0b", "#52514e", "#e6e5e0"
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
                     "grid.color": GRID, "axes.axisbelow": True, "legend.frameon": False})
fig, ax = plt.subplots(figsize=(8, 3.8))
xs = [0, 1, 2.6, 3.6, 4.6]
for x, n in zip(xs, names):
    m = res[n]
    col = GRAY if n.endswith("_rr") else BLUE
    ax.bar(x, st.mean(m), width=0.7, color=col)
    ax.errorbar(x, st.mean(m), yerr=[[st.mean(m) - min(m)], [max(m) - st.mean(m)]], color=INK, capsize=4, lw=1)
    ax.scatter(x, predicted(n), marker="_", s=500, color=INK, linewidth=2, zorder=4)
    ax.text(x, max(m) + 0.4, f"{st.mean(m):.1f} s", ha="center", fontsize=9, color=INK)
ax.set_xticks(xs, ["A\nRound-Robin", "A\nopt", "B\nRound-Robin", "B\nLPT", "B\nopt"])
ax.set_ylabel("makespan (s)")
ax.scatter([], [], marker="_", s=300, color=INK, linewidth=2, label="prédit par le modèle")
ax.errorbar([], [], yerr=[], color=INK, capsize=4, lw=1, label=f"mesuré : moyenne, min – max sur {len(reps)} runs")
ax.legend(fontsize=8.5, loc="upper left")
ax.set_ylim(0, max(max(v) for v in res.values()) * 1.18)
g = {sc: 100 * (1 - st.mean(res[sc + "_opt"]) / st.mean(res[sc + "_rr"])) for sc in "AB"}
ax.set_title(f"Sur les vraies VMs : opt finit {g['A']:.0f} % (A) et {g['B']:.0f} % (B) plus tôt que Round-Robin")
fig.tight_layout()
for d in (S, os.path.join(ROOT, "results")):
    fig.savefig(os.path.join(d, "fig_real_run.png"), dpi=150)
print("written: results/fig_real_run.png")
