#!/usr/bin/env python3
"""make_figures.py — README figures from the measured runs and the optimiser's outputs.
Usage: python3 scripts/make_figures.py   (needs matplotlib; writes results/fig_*.png)
Reads results/td3|td4 (measured runs, via makespan.sh), results/model_fit.md, results/scaling.csv,
and runs bin/optimizer for the scenario predictions. Nothing is typed in by hand."""
import csv, os, re, subprocess, statistics as st
from collections import defaultdict
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
BLUE, ORANGE, AQUA, GRAY = "#2a78d6", "#eb6834", "#1baf7a", "#9a9890"
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e6e5e0"
plt.rcParams.update({"font.size": 10, "axes.edgecolor": INK2, "axes.labelcolor": INK2, "xtick.color": INK2,
                     "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8, "axes.axisbelow": True,
                     "figure.facecolor": "white", "axes.facecolor": "white", "axes.titlecolor": INK,
                     "axes.titlesize": 11, "legend.frameon": False})


def save(fig, name):
    fig.tight_layout()
    fig.savefig(f"results/{name}", dpi=150)
    plt.close(fig)
    print("written: results/" + name)


def measured(run):
    out = subprocess.run(["bash", "scripts/makespan.sh", run], capture_output=True, text=True).stdout
    fin = {l.split()[0]: float(l.split()[3]) for l in out.splitlines() if l.startswith("cloudopt-")}
    return fin, float(re.search(r"measured makespan: ([0-9.]+)", out).group(1))


def predict(method, tasks):
    out = subprocess.run(["bin/optimizer", "-method", method, "-tasks", tasks], capture_output=True, text=True).stdout
    d = dict(kv.split("=") for kv in re.search(r"^summary (.*)$", out, re.M).group(1).split())
    return float(d["makespan"]), float(d["lower_bound"])


# 1. TD3-TD4: same 9 tasks, three placements, measured finish time of each VM
runs = [("results/td4/allocation_rr", "Round-Robin (TD4)"), ("results/td4/allocation_rr_reordered", "Round-Robin, fichier réordonné"),
        ("results/td3/allocation_manual_packed", "7 tâches sur vm1 (TD3)")]
fig, axs = plt.subplots(1, 3, figsize=(11, 3.4), sharey=True)
for ax, (run, title) in zip(axs, runs):
    fin, ms = measured(run)
    vms = ["cloudopt-vm1", "cloudopt-vm2", "cloudopt-vm3"]
    vals = [fin.get(v, 0) for v in vms]
    cols = [BLUE if v == max(vals) else GRAY for v in vals]
    ax.bar(["vm1\ne2-std-2", "vm2\ne2-medium", "vm3\ne2-medium"], vals, 0.55, color=cols, edgecolor="white", linewidth=2)
    for x, v in enumerate(vals):
        ax.text(x, v + 0.4, f"{v:.1f} s", ha="center", color=INK, fontsize=9)
    ax.set_title(f"{title}\nmakespan mesuré {ms:.1f} s", fontsize=10)
axs[0].set_ylabel("fin de la dernière tâche (s)")
fig.suptitle("Mêmes 9 tâches, trois placements : le goulot (en bleu) change, le makespan aussi", color=INK, fontsize=11)
save(fig, "fig_td4_placements.png")

# 2. duration model: predicted vs measured, 12 VM points, two hypotheses
pts = []
for line in open("results/model_fit.md"):
    m = re.match(r"\| results/\S+ \| \S+ \| \d+ \| ([0-9.]+) \| ([0-9.]+) \| ([0-9.]+) \|", line)
    if m:
        pts.append(tuple(map(float, m.groups())))
fit = {k: v for k, v in re.findall(r"\| (H[12]) [^|]*\| ([0-9.]+) \|", open("results/model_fit.md").read())}
mae = re.findall(r"\| H[12] [^|]*\| [0-9.]+ \| ([0-9.]+) s \|", open("results/model_fit.md").read())
fig, ax = plt.subplots(figsize=(5.2, 4.6))
lim = max(max(p) for p in pts) + 2
ax.plot([0, lim], [0, lim], color=INK2, lw=1, ls="--")
ax.text(lim - 0.5, lim - 1.6, "prédit = mesuré", ha="right", color=INK2, fontsize=8)
ax.scatter([p[0] for p in pts], [p[1] for p in pts], s=42, color=ORANGE, edgecolor="white", linewidth=1.5,
           label=f"H1 : colonne de chaque type, c = {fit['H1']}  (erreur moy. {mae[0]} s)")
ax.scatter([p[0] for p in pts], [p[2] for p in pts], s=42, color=BLUE, edgecolor="white", linewidth=1.5,
           label=f"H2 : vitesse e2-standard-2, c = {fit['H2']}  (erreur moy. {mae[1]} s)")
ax.set_xlim(0, lim); ax.set_ylim(0, lim)
ax.set_xlabel("temps de fin mesuré d'une VM (s)"); ax.set_ylabel("temps de fin prédit (s)")
ax.set_title("Modèle de durée : 12 points mesurés (TD3 + TD4)")
ax.legend(loc="lower right", fontsize=8)
save(fig, "fig_model_fit.png")

# 3. scenarios: Round-Robin vs LPT vs opt (predicted), lower bound
sc = [("A : 9 tâches TD3-TD4", "data/tasks.csv"), ("A réordonné", "data/tasks_reordered.csv"), ("B : 10 tâches", "data/tasks_b.csv")]
meth = [("rr", "Round-Robin (baseline)", GRAY), ("lpt", "LPT (CM3)", ORANGE), ("opt", "opt (CM3+CM5+CM4)", BLUE)]
fig, ax = plt.subplots(figsize=(8, 3.8))
w = 0.26
for k, (mt, lab, col) in enumerate(meth):
    vals = [predict(mt, t)[0] for _, t in sc]
    xs = [i + (k - 1) * w for i in range(len(sc))]
    ax.bar(xs, vals, w - 0.02, color=col, label=lab, edgecolor="white", linewidth=2)
    for x, v in zip(xs, vals):
        ax.text(x, v + 0.3, f"{v:.1f}", ha="center", fontsize=8.5, color=INK)
for i, (_, t) in enumerate(sc):
    lb = predict("opt", t)[1]
    ax.plot([i - 1.5 * w, i + 1.5 * w], [lb, lb], color=INK, lw=1.2, ls=":", label="borne inférieure" if i == 0 else None)
ax.set_xticks(range(len(sc)), [s for s, _ in sc])
ax.set_ylabel("makespan prédit (s)")
ax.set_title("Makespan prédit par placement (mesuré pour RR : 15,8 s et 18,7 s)")
ax.legend(loc="upper left", fontsize=8.5, ncols=4)
ax.set_ylim(0, 25)
save(fig, "fig_opt_scenarios.png")

# 4. quality against the proved optimum (40 small instances)
rows = list(csv.DictReader(open("results/scaling.csv")))
q = defaultdict(list)
for r in rows:
    if r["part"] == "quality":
        q[r["method"]].append(float(r["gap_to_opt_pct"]))
order = [("rr", "Round-Robin"), ("minmin", "Min-Min"), ("maxmin", "Max-Min"), ("lpt", "LPT"),
         ("ls", "LPT + descente"), ("ils", "+ recherche itérée (opt)")]
fig, ax = plt.subplots(figsize=(7.5, 3.4))
names = [n for _, n in order][::-1]
vals = [st.mean(q[k]) for k, _ in order][::-1]
hits = [sum(g < 1e-6 for g in q[k]) for k, _ in order][::-1]
tot = [len(q[k]) for k, _ in order][::-1]
ax.barh(names, vals, 0.55, color=[BLUE if n.startswith("+") else GRAY for n in names], edgecolor="white", linewidth=2)
for y, (v, h, t) in enumerate(zip(vals, hits, tot)):
    ax.text(v + 0.8, y, f"{v:.1f} %   (optimum trouvé {h}/{t})" if v >= 0.05 else f"< 0,1 %   (optimum trouvé {h}/{t})", va="center", fontsize=8.5, color=INK)
ax.set_xlim(0, 80)
ax.set_xlabel("écart moyen à l'optimum prouvé (%)")
ax.set_title("Qualité sur 40 petites instances dont on connaît l'optimum")
ax.grid(axis="y", visible=False)
save(fig, "fig_quality.png")

# 5. scale: computation time and gap to the lower bound, two panels (no dual axis)
sc_rows = [r for r in rows if r["part"] == "scale" and r["status"] != "INFEASIBLE"]
sizes = sorted({int(r["tasks"]) for r in sc_rows})
fig, (a, b) = plt.subplots(1, 2, figsize=(11, 3.8))
for mt, lab, col in [("greedy", "glouton (CM3)", ORANGE), ("ils", "+ recherche locale itérée (CM5)", AQUA), ("opt", "opt complet (+ CM4, limite 10 s)", BLUE)]:
    t = [max(float(r["time_ms"]) for r in sc_rows if r["method"] == mt and int(r["tasks"]) == n) / 1000 for n in sizes]
    g = [st.mean(float(r["gap_to_lb_pct"]) for r in sc_rows if r["method"] == mt and int(r["tasks"]) == n) for n in sizes]
    a.plot(sizes, t, color=col, lw=2, marker="o", ms=6, mec="white", label=lab)
    if mt != "ils":
        b.plot(sizes, g, color=col, lw=2, marker="o", ms=6, mec="white", label=lab)
a.set_xscale("log"); a.set_yscale("log")
a.set_xlabel("nombre de tâches (≈ 5 par VM)"); a.set_ylabel("temps de calcul max (s)")
a.set_title("Temps de calcul : borné par la limite de 10 s")
a.axhline(10, color=INK2, lw=1, ls="--"); a.text(sizes[0], 12, "limite 10 s", fontsize=8, color=INK2)
a.legend(fontsize=8, loc="lower right")
b.set_xscale("log")
b.set_xlabel("nombre de tâches (≈ 5 par VM)"); b.set_ylabel("écart à la borne inférieure (%)")
b.set_title("Écart à la borne (majorant de l'écart à l'optimum)")
b.legend(fontsize=8)
for ax in (a, b):
    ax.set_xticks(sizes, [str(n) for n in sizes]); ax.minorticks_off()
save(fig, "fig_scaling.png")
