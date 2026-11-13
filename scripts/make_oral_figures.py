#!/usr/bin/env python3
"""make_oral_figures.py — the README / oral figures: one message per figure, written as its title.
Usage: python3 scripts/make_oral_figures.py [COMPARE_SESSION] [BURST_SESSION]   (default: latest of each)
Reads only measured data and the optimiser (bin/optimizer, `make optimizer`); writes results/oral_*.png.
  oral_td2_machines   same program, 3 machines: each task slows down differently (p_ij)
  oral_model          the duration model against every measured VM finish time
  oral_gantt_b        WHY the optimiser wins: who runs where, measured, scenario B
  oral_real_run       Round-Robin vs optimiser on the real VMs, 5 runs each
  oral_quality        how close to the proven optimum, 40 instances
  oral_scaling        1000 tasks: answer in <= 10 s, close to the best possible
  oral_burst_when     when does an e2-medium burst? (measured)
  oral_burst_how      what it is based on: a reserve of burst seconds (model calibrated on the measures)
  oral_trio           Round-Robin -> optimiser -> optimiser + shared cores: time, money, batches per dollar
  oral_burst_rule     when to rent an e2-medium (cost of the work vs job length and occupation)"""
import csv, glob, json, os, re, statistics as st, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
CS = sys.argv[1] if len(sys.argv) > 1 else sorted(glob.glob("results/project/session_*"))[-1]
BS = sys.argv[2] if len(sys.argv) > 2 else sorted(glob.glob("results/burst/session_*"))[-1]
OUT = "results"
SLIDES = os.environ.get("SLIDES") == "1"     # slide versions: no title (the slide says it), deck blue -> results/slides/
if SLIDES:
    OUT = "results/slides"
    os.makedirs(OUT, exist_ok=True)
PS, PM = 0.0737, 0.0369                      # $/h europe-west1 on demand: e2-standard-2, e2-medium

import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

# palette (validated categorical order; gray = baseline / context, never a series of its own)
BLUE, ORANGE, AQUA, GRAY = "#2a78d6", "#eb6834", "#1baf7a", "#9a9890"
ORANGE_L, BLUE_L, GRAY_L = "#f7c3ad", "#b5d0f2", "#dddcd8"
if SLIDES:
    BLUE, BLUE_L = "#3a4bf0", "#c3c8fb"
INK, INK2, INK3, GRID, SURF = "#0b0b0b", "#52514e", "#8a8984", "#ebeae6", "#ffffff"
plt.rcParams.update({"font.size": 12, "axes.spines.top": False, "axes.spines.right": False, "axes.spines.left": False,
                     "axes.grid": True, "grid.color": GRID, "axes.axisbelow": True, "legend.frameon": False,
                     "axes.edgecolor": INK3, "xtick.color": INK2, "ytick.color": INK2, "axes.labelcolor": INK2,
                     "axes.titlesize": 13, "axes.titlecolor": INK, "text.parse_math": False, "figure.facecolor": SURF, "axes.facecolor": SURF})


def head(fig, title, sub=None):
    """the figure's message as its title (left-aligned), how to read it as a subtitle"""
    if SLIDES:
        return
    fig.text(0.012, 0.975, title, fontsize=17, fontweight="bold", color=INK, va="top", ha="left")
    if sub:
        fig.text(0.012, 0.915 if "\n" not in title else 0.86, sub, fontsize=11.5, color=INK2, va="top", ha="left")


def save(fig, name, top=0.80, bottom=None):
    if SLIDES:
        top = min(0.95, top + 0.15)
    fig.subplots_adjust(top=top, bottom=bottom)
    fig.savefig(os.path.join(OUT, name + ".png"), dpi=150)
    plt.close(fig)
    print("written:", os.path.join(OUT, name + ".png"))


def fr(x, d=1):
    return f"{x:.{d}f}".replace(".", ",")


def opt_run(method, tasks, vms, p):
    o = subprocess.run(["bin/optimizer", "-method", method, "-tasks", tasks, "-vms", vms, "-p", p],
                       capture_output=True, text=True).stdout
    return float(re.search(r"makespan=([0-9.]+)", o).group(1))


def metas(run):
    out = []
    for f in glob.glob(os.path.join(run, "*.meta")):
        kv = dict(x.strip().split("=", 1) for x in open(f) if "=" in x)
        out.append(kv)
    return out


def makespan(run):
    m = metas(run)
    return max(float(k["end_epoch"]) for k in m) - min(float(k["launch_epoch"]) for k in m)


reps = sorted(glob.glob(os.path.join(CS, "rep*")))
NAMES = ["A_rr", "A_opt", "B_rr", "B_lpt", "B_opt"]
meas = {n: [makespan(os.path.join(r, n)) for r in reps if os.path.isdir(os.path.join(r, n))] for n in NAMES}
P_NOW = next(f for f in (os.path.join(CS, "p_matrix_now_corrected.csv"), os.path.join(CS, "p_matrix_now.csv")) if os.path.exists(f))
VMS_NOW = os.path.join(CS, "vms_now.csv")
TASKS = {"A": "data/tasks.csv", "B": "data/tasks_b.csv"}

# ---------------------------------------------------------------------------------------------- TD2
rows = {r["task"]: r for r in csv.DictReader(open("data/p_matrix.csv"))}
pick = [("cpu_task:10000000", "calcul\n(cpu 10M)"), ("matrix_task:1500", "matrices\n(matrix 1500)"),
        ("memory_task:1024", "mémoire\n(memory 1 Go)"), ("sort_task:20000000", "tri\n(sort 20M)")]
mach = [("local", "portable (Ryzen 7)", GRAY), ("cloud_vm1_std2", "GCP e2-standard-2", BLUE),
        ("cloud_vm1", "GCP e2-medium (moyenne TD2)", ORANGE)]
fig, ax = plt.subplots(figsize=(11, 5.2))
h = 0.26
for gi, (task, lab) in enumerate(pick):
    for mi, (col, name, c) in enumerate(mach):
        v = float(rows[task][col])
        y = gi + (mi - 1) * h
        ax.barh(y, v, height=h - 0.03, color=c)
        ax.text(v + 0.25, y, f"{fr(v)} s", va="center", fontsize=10.5, color=INK)
ax.set_yticks(range(len(pick)), [l for _, l in pick]); ax.invert_yaxis()
ax.set_xlabel("durée d'une exécution (s)"); ax.grid(axis="y", visible=False)
ax.legend(handles=[Patch(color=c, label=n) for _, n, c in mach], loc="lower right", fontsize=11)
head(fig, "Même programme, 3 machines : chaque tâche ralentit différemment",
     "Le portable écrase le cloud sur le calcul, pas sur la mémoire : la durée dépend du couple tâche × machine (c'est p_ij).\n"
     "Mesures TD2, 3 runs. L'e2-medium mélange des runs en burst et à sec (voir le bonus) : d'où ses ×2.")
save(fig, "oral_td2_machines", top=0.80)

# ---------------------------------------------------------------------------------------------- model
pts = []                                         # (predicted, measured) per VM finish, TD3/TD4 fit
mf = "results/model_fit.md"
fit = json.load(open("results/model_fit.json")) if os.path.exists("results/model_fit.json") else None
tmp = tempfile.mkdtemp()
for n in NAMES:                                  # today's session: every VM of every run
    alloc = os.path.join(CS, "alloc", n + ".csv")
    o = subprocess.run(["bin/optimizer", "-method", "eval", "-tasks", TASKS[n[0]], "-vms", VMS_NOW, "-p", P_NOW,
                        "-alloc", alloc], capture_output=True, text=True).stdout
    pred = {l.split()[0]: float(l.split()[6]) for l in o.splitlines() if l.startswith("cloudopt-vm")}
    for r in reps:
        m = metas(os.path.join(r, n))
        if not m:
            continue
        t0 = min(float(k["launch_epoch"]) for k in m)
        for vm, pv in pred.items():
            ends = [float(k["end_epoch"]) for k in m if k["vm"] == vm]
            if ends:
                pts.append((pv, max(ends) - t0))
err = st.mean(abs(a - b) for a, b in pts)
fig, ax = plt.subplots(figsize=(8.5, 6.2))
lim = max(max(a, b) for a, b in pts) * 1.08
ax.fill_between([0, lim], [-1, lim - 1], [1, lim + 1], color=BLUE_L, alpha=0.45, lw=0)
ax.plot([0, lim], [0, lim], color=INK3, lw=1, ls="--")
ax.scatter([b for a, b in pts], [a for a, b in pts], s=46, color=BLUE, edgecolor="white", linewidth=1.2, zorder=3)
ax.text(lim * 0.97, lim * 0.97 - 0.2, "prédit = mesuré", ha="right", va="top", fontsize=10.5, color=INK2, rotation=0)
ax.text(lim * 0.62, lim * 0.62 - 2.6, "zone ±1 s", fontsize=10.5, color=BLUE)
out_ = max(pts, key=lambda x: x[1] - x[0])
if out_[1] - out_[0] > 2:
    ax.annotate("un run lent : variabilité du cloud", (out_[1], out_[0]), (out_[1] - 0.5, out_[0] - 3.5), ha="right",
                fontsize=10, color=INK2, arrowprops=dict(arrowstyle="-", color=INK3, lw=0.8))
ax.set_xlim(0, lim); ax.set_ylim(0, lim)
ax.set_xlabel("temps de fin MESURÉ d'une VM (s)"); ax.set_ylabel("temps de fin PRÉDIT par le modèle (s)")
head(fig, f"Le modèle prédit le temps réel à {fr(err)} s près",
     f"{len(pts)} temps de fin de VM mesurés le 13/11 ({len(reps)} répétitions × 5 plans × 3 VMs).\n"
     "Chaque point est une VM ; sur la diagonale, la prédiction est parfaite.")
save(fig, "oral_model", top=0.80)

# ---------------------------------------------------------------------------------------------- gantt
def median_rep(n):
    ms = [(makespan(os.path.join(r, n)), r) for r in reps]
    return sorted(ms)[len(ms) // 2][1]


VMLAB = {"cloudopt-vm1": "vm1\ne2-standard-2", "cloudopt-vm2": "vm2\ne2-medium", "cloudopt-vm3": "vm3\ne2-medium"}
fig, axs = plt.subplots(1, 2, figsize=(13, 5.4), sharex=True)
xmax = 0
for ax, n, title in [(axs[0], "B_rr", "Round-Robin"), (axs[1], "B_opt", "Optimiseur (opt)")]:
    m = metas(os.path.join(median_rep(n), n))
    t0 = min(float(k["launch_epoch"]) for k in m)
    y, ticks, labs = 0, [], []
    vend = {}
    for vm in ["cloudopt-vm1", "cloudopt-vm2", "cloudopt-vm3"]:
        ks = sorted([k for k in m if k["vm"] == vm], key=lambda k: -float(k["end_epoch"]))
        first = y
        for k in ks:
            s, e = float(k["remote_start_epoch"]) - t0, float(k["end_epoch"]) - t0
            l = float(k["launch_epoch"]) - t0
            ax.barh(y, s - l, left=l, height=0.72, color=GRAY_L)
            ax.barh(y, e - s, left=s, height=0.72, color=BLUE if n == "B_opt" else GRAY)
            short = k["workload"].replace("_task", "") + " " + (k["size"][:-6] + "M" if len(k["size"]) > 6 else k["size"])
            ax.text(e + 0.25, y, short, va="center", fontsize=9, color=INK2)
            y += 1
        vend[vm] = max(float(k["end_epoch"]) - t0 for k in ks)
        ticks.append((first + y - 1) / 2); labs.append(VMLAB[vm])
        ax.axhline(y - 0.5 + 0.5, color=INK3, lw=0.6) if vm != "cloudopt-vm3" else None
        y += 1
    ms = max(vend.values())
    xmax = max(xmax, ms)
    ax.axvline(ms, color=ORANGE, lw=2)
    ax.text(ms, -1.1, f" fin : {fr(ms)} s", color=ORANGE, fontsize=12, fontweight="bold", va="center")
    ax.set_yticks(ticks, labs); ax.invert_yaxis(); ax.grid(axis="y", visible=False)
    ax.set_title(title, loc="left", fontsize=14, fontweight="bold")
    ax.set_xlabel("secondes depuis le lancement du lot")
for ax in axs:
    ax.set_xlim(0, xmax * 1.22)
fig.legend(handles=[Patch(color=GRAY_L, label="connexion SSH"), Patch(color=GRAY, label="calcul (Round-Robin)"),
                    Patch(color=BLUE, label="calcul (optimiseur)")], fontsize=10.5,
           **({"loc": "lower center", "bbox_to_anchor": (0.55, 0.0), "ncol": 3} if SLIDES else {"loc": "upper right", "bbox_to_anchor": (0.99, 0.99)}))
fig.subplots_adjust(left=0.1, wspace=0.28, right=0.98)
gb = 100 * (1 - st.median(meas["B_opt"]) / st.median(meas["B_rr"]))
head(fig, f"Pourquoi l'optimiseur gagne : il équilibre les 3 VMs ({fr(-gb, 0)} %)",
     "Scénario B, 10 tâches, run réel (répétition médiane). Une barre = une tâche, de son lancement à sa fin.\n"
     "Round-Robin distribue à tour de rôle : une VM finit tard pendant que les autres attendent.")
save(fig, "oral_gantt_b", top=0.78, bottom=0.2 if SLIDES else None)

# ---------------------------------------------------------------------------------------------- real run
fig, axs = plt.subplots(1, 2, figsize=(12, 5), gridspec_kw={"width_ratios": [2, 3]})
for ax, sc, ns in [(axs[0], "A", ["A_rr", "A_opt"]), (axs[1], "B", ["B_rr", "B_lpt", "B_opt"])]:
    lab = {"rr": "Round-Robin", "lpt": "LPT\n(même plan)", "opt": "Optimiseur\n(opt)"}
    rr = st.median(meas[sc + "_rr"])
    for i, n in enumerate(ns):
        v = meas[n]
        c = GRAY if n.endswith("_rr") else (BLUE if n.endswith("_opt") else BLUE_L)
        ax.bar(i, st.median(v), width=0.62, color=c)
        ax.plot([i, i], [min(v), max(v)], color=INK, lw=1.4)
        ax.plot([i - 0.08, i + 0.08], [min(v)] * 2, color=INK, lw=1.4); ax.plot([i - 0.08, i + 0.08], [max(v)] * 2, color=INK, lw=1.4)
        g = "" if n.endswith("_rr") else f"\n{fr(100 * (st.median(v) - rr) / rr, 0)} %"
        ax.text(i, max(v) + 0.5, f"{fr(st.median(v))} s{g}", ha="center", va="bottom", fontsize=12.5,
                fontweight="bold" if n.endswith("_opt") else "normal", color=INK)
    ax.set_xticks(range(len(ns)), [lab[n[2:]] for n in ns])
    ax.set_ylim(0, 29); ax.grid(axis="x", visible=False)
    ax.set_title(f"Scénario {sc} : {9 if sc == 'A' else 10} tâches", loc="left", fontweight="bold")
axs[0].set_ylabel("temps pour finir le lot (s)")
ga = 100 * (1 - st.median(meas["A_opt"]) / st.median(meas["A_rr"]))
head(fig, f"Sur les vraies VMs, l'optimiseur finit {fr(ga, 0)} à {fr(gb, 0)} % plus tôt que Round-Robin",
     f"Mesuré le 13/11 : {len(reps)} runs par plan ; barre = médiane, trait = du plus rapide au plus lent.\n"
     "Les traits ne se recouvrent pas : le gain n'est pas du bruit.")
save(fig, "oral_real_run", top=0.78)

# ---------------------------------------------------------------------------------------------- quality
q = [r for r in csv.DictReader(open("results/scaling.csv")) if r["part"] == "quality"]
meth = [("rr", "Round-Robin"), ("minmin", "Min-Min"), ("maxmin", "Max-Min"), ("lpt", "LPT"), ("ls", "LPT + descente"),
        ("ils", "Recherche locale itérée")]
fig, ax = plt.subplots(figsize=(11, 4.8))
for i, (mk, lab) in enumerate(meth):
    rs = [r for r in q if r["method"] == mk]
    ok = [r for r in rs if r["gap_to_opt_pct"] not in ("", None)]
    found = sum(float(r["gap_to_opt_pct"]) < 1e-6 for r in ok)
    c = BLUE if mk == "ils" else GRAY
    ax.barh(i, found, height=0.62, color=c)
    inf = 40 - len(ok)
    ax.text(found + 0.5, i, f"{found} / 40" + (f"   ({inf} plans infaisables : RAM dépassée)" if inf else ""), va="center",
            fontsize=12, fontweight="bold" if mk == "ils" else "normal", color=INK)
ax.set_yticks(range(len(meth)), [l for _, l in meth]); ax.invert_yaxis()
ax.set_xlim(0, 52); ax.set_xlabel("nombre d'instances où la méthode trouve LE meilleur plan possible (sur 40)")
ax.grid(axis="y", visible=False)
head(fig, "La recherche locale itérée trouve le meilleur plan possible 39 fois sur 40",
     "40 petits problèmes résolus exactement par le branch and bound (lui-même vérifié par force brute sur 8 cas).")
save(fig, "oral_quality", top=0.80)

# ---------------------------------------------------------------------------------------------- scaling
import math
sc_ = [r for r in csv.DictReader(open("results/scaling.csv")) if r["part"] == "scale"]
sizes = sorted({int(r["tasks"]) for r in sc_})
vms = {int(r["tasks"]): int(r["vms"]) for r in sc_}
xl = [f"{n}\n({vms[n]} VMs)" for n in sizes]
expo = [n * math.log10(vms[n]) for n in sizes]                     # M^N plans = 10^expo
tt = [st.median(float(r["time_ms"]) for r in sc_ if int(r["tasks"]) == n and r["method"] == "opt") / 1000 for n in sizes]
fig, axs = plt.subplots(1, 2, figsize=(14, 5.4))
axs[0].bar(range(len(sizes)), expo, color=GRAY, width=0.62)
for i, e in enumerate(expo):
    axs[0].text(i, e + 40, f"10^{e:.0f}", ha="center", fontsize=11, color=INK)
axs[0].set_ylabel("nombre de chiffres du nombre de plans")
axs[0].set_title("« Tout essayer » : plans à tester", loc="left", fontweight="bold")
axs[0].set_ylim(0, max(expo) * 1.15)
axs[1].bar(range(len(sizes)), tt, color=BLUE, width=0.62)
for i, v in enumerate(tt):
    axs[1].text(i, v + 0.2, (f"{v * 1000:.0f} ms" if v < 1 else f"{fr(v, 0)} s"), ha="center", fontsize=11, color=INK)
axs[1].axhline(10, color=ORANGE, lw=1.5, ls="--"); axs[1].text(-0.4, 10.3, "limite fixée : 10 s", color=ORANGE, fontsize=10.5)
axs[1].set_ylim(0, 12.5); axs[1].set_ylabel("temps de calcul (s, médiane de 3)")
axs[1].set_title("Notre optimiseur : temps pour rendre un plan", loc="left", fontweight="bold")
for ax in axs:
    ax.set_xticks(range(len(sizes)), xl, fontsize=10); ax.grid(axis="x", visible=False); ax.set_xlabel("nombre de tâches")
head(fig, "Tout essayer est impossible ; l'optimiseur répond en ~10 s, même à 1000 tâches",
     "À 1 milliard de plans par seconde, 50 tâches prendraient déjà 10^33 années. Qualité : prouvé optimal sur nos lots,\n"
     "39 fois sur 40 sur les petits cas, et à moins de 2 % de la borne inférieure à 500-1000 tâches. Round-Robin : infaisable dès 50 tâches (RAM).")
save(fig, "oral_scaling", top=0.77, bottom=0.17)

# ---------------------------------------------------------------------------------------------- burst: when
sys.argv = ["x", BS]
import io, contextlib
with contextlib.redirect_stdout(io.StringIO()):
    import runpy
    BA = runpy.run_path("scripts/burst_analysis.py")
BP = json.load(open(os.path.join(BS, "burst_params.json")))["phases"]
d2, s2 = BP["deplete|cloudopt-vm2"], BP["deplete|cloudopt-vm1"]
b, base, std = d2["initial_speed"], d2["final_speed"], s2["final_speed"]
TB = d2["burst_s"]
fig, ax = plt.subplots(figsize=(12, 5.2))
for vm, lab, col in [("cloudopt-vm1", "e2-standard-2 (0,0737 $/h)", BLUE), ("cloudopt-vm2", "e2-medium (0,0369 $/h)", ORANGE)]:
    sp, _ = BA["series"](("deplete", vm))
    ax.plot([t for t, _ in sp][3:], BA["smooth"]([s for _, s in sp], 8)[3:], color=col, lw=2.6)
    ax.text(sp[-1][0] + 4, BA["smooth"]([s for _, s in sp], 8)[-1], lab, color=col, fontsize=11.5, va="center", fontweight="bold")
ax.axvspan(0, TB, color=ORANGE_L, alpha=0.35, lw=0)
ax.text(TB / 2, 0.25, "BURST\nmême vitesse,\nmoitié prix", ha="center", fontsize=13, fontweight="bold", color=INK)
ax.text(TB + (420 - TB) / 2, 0.25, "À SEC : moitié vitesse, moitié prix", ha="center", fontsize=13, fontweight="bold", color=INK)
ax.annotate("", (TB + 14, base + 0.06), (TB + 14, b - 0.06), arrowprops=dict(arrowstyle="->", color=INK, lw=1.5))
ax.text(TB + 20, (b + base) / 2, f"÷ 2 après {fr(TB, 0)} s", fontsize=12, color=INK, va="center")
ax.set_xlim(0, 540); ax.set_ylim(0, 1.65)
ax.set_xlabel("secondes de calcul continu, après 10 min de repos")
ax.set_ylabel("vitesse de calcul (cœurs à pleine vitesse)")
ax.set_xticks([0, 60, 120, 180, 240, 300, 360, 420])
head(fig, f"Une e2-medium « burste » ~{fr(TB / 60, 0)} min, puis tombe à la moitié",
     "Mesuré le 13/11 : même calcul en continu sur les deux VMs. Avec 1 seul cœur occupé, c'est pareil : 0,96 puis 0,48.\n"
     "Linux ne voit rien (« steal » à 0) : seule la vitesse mesurée révèle le freinage.")
save(fig, "oral_burst_when", top=0.79)

# ---------------------------------------------------------------------------------------------- burst: how (model)
rho = 1.0                                   # s of burst regained per idle second (1-vCPU probe: 61 s after 60 s)
try:
    txt = open("results/burst_study.md").read()
    rho = float(re.search(r"Recharge : ([0-9.]+) s de burst", txt).group(1))
except Exception:
    pass
plan = [("repos", 0, 150), ("calcul", 150, 420), ("repos", 420, 480), ("calcul", 480, 600)]
T, SPD, RES = [], [], []
res = 0.0
for kind, a, z in plan:
    for t in range(a, z):
        if kind == "repos":
            res = min(TB, res + rho); s = 0
        elif res > 0:
            res = max(0.0, res - 1); s = b
        else:
            s = base
        T.append(t); SPD.append(s); RES.append(res)
fig, (a1, a2) = plt.subplots(2, 1, figsize=(12, 6.4), sharex=True, gridspec_kw={"height_ratios": [1.15, 1]})
a1.step(T, [std if any(k == "calcul" and a <= t < z for k, a, z in plan) else 0 for t in T], where="post", color=BLUE, lw=1.8, ls="--")
a1.step(T, SPD, where="post", color=ORANGE, lw=2.6)
a1.text(600, std + 0.08, "e2-standard-2", color=BLUE, ha="right", fontsize=11)
a1.text(600, base - 0.22, "e2-medium", color=ORANGE, ha="right", fontsize=11, fontweight="bold")
a1.set_ylabel("vitesse"); a1.set_ylim(0, 1.75)
a2.fill_between(T, RES, step="post", color=ORANGE_L, lw=0)
a2.step(T, RES, where="post", color=ORANGE, lw=2)
a2.set_ylabel("réserve de burst (s)"); a2.set_ylim(0, TB * 1.55)
a2.axhline(TB, color=INK3, lw=0.8, ls=":"); a2.text(345, TB + 4, f"réserve pleine : {fr(TB, 0)} s", fontsize=10, color=INK2, ha="center")
for kind, a, z in plan:
    for ax in (a1, a2):
        if kind == "repos":
            ax.axvspan(a, z, color=GRAY_L, alpha=0.45, lw=0)
    a1.text((a + z) / 2, 1.6, kind.upper(), ha="center", fontsize=11, fontweight="bold", color=INK2)
a2.annotate("repos : la réserve se remplit\n(1 s gagnée par s de repos)", (75, TB * 1.22), fontsize=10.5, color=INK, ha="center")
a2.annotate("calcul en burst :\nla réserve se vide", (215, TB * 1.22), fontsize=10.5, color=INK, ha="center")
a2.annotate("réserve vide :\nmoitié vitesse", (345, 30), fontsize=10.5, color=INK, ha="center")
a2.annotate("1 min de repos =\n1 min de burst", (510, TB * 1.22), fontsize=10.5, color=INK, ha="center")
a2.set_xlabel("secondes")
head(fig, "Sur quoi ça se base : une réserve de secondes de burst",
     f"Modèle calé sur nos mesures : réserve pleine = {fr(TB, 0)} s, recharge = {fr(rho, 2)} s par seconde de repos.\n"
     "La VM va à pleine vitesse tant que sa réserve n'est pas vide (en gris : la VM ne calcule pas).")
save(fig, "oral_burst_how", top=0.80)

# ---------------------------------------------------------------------------------------------- trio
tmpd = tempfile.mkdtemp()
pf = os.path.join(tmpd, "p.csv")
with open(pf, "w") as f:
    f.write("task,std2,med_burst,med_empty\n")
    for r in csv.DictReader(open(P_NOW)):
        f.write(f"{r['task']},{r['gce_std2_now']},{r['gce_medium_now']},{float(r['gce_medium_now']) * b / base}\n")


def fleet(n_std, n_med, col):
    vf = os.path.join(tmpd, f"v{n_std}{n_med}{col}.csv")
    with open(vf, "w") as f:
        f.write("vm,machine_type,ram_mb,p_column,eff_cores\n")
        for i in range(n_std):
            f.write(f"cloudopt-s{i + 1},e2-standard-2,8192,std2,1.25\n")
        for i in range(n_med):
            f.write(f"cloudopt-m{i + 1},e2-medium,4096,{col},1.25\n")
    return vf


CFG = [("Round-Robin\n3 VMs dédiées", "rr", (3, 0), "med_burst", GRAY, None),
       ("Optimiseur\n3 VMs dédiées", "opt", (3, 0), "med_burst", BLUE, None),
       ("Optimiseur +\ncœurs partagés\n(1 dédiée + 2 e2-medium)", "opt", (1, 2), "med_burst", ORANGE, None),
       ("même flotte,\ne2-medium à sec", "opt", (1, 2), "med_empty", "none", ORANGE)]
tri = {}
for sc in "AB":
    tri[sc] = []
    for lab, m, (ns, nm), col, c, ec in CFG:
        t = opt_run(m, TASKS[sc], fleet(ns, nm, col), pf)
        price = ns * PS + nm * PM
        tri[sc].append((lab, t, price * t / 3.6, c, ec))          # $ for 1000 batches
measB = st.mean(meas["B_opt"])
fig, axs = plt.subplots(1, 3, figsize=(16.5, 6))
panels = [("Temps d'un lot (s)", lambda x: x[1], lambda v: f"{fr(v)} s"),
          ("Coût de 1000 lots ($)", lambda x: x[2], lambda v: f"{fr(v, 2)} $"),
          ("Lots calculés pour 1 $", lambda x: 1000 / x[2], lambda v: f"{v:.0f}")]
base_ = tri["B"][0]
for ax, (ttl, fget, fmt) in zip(axs, panels):
    vals = [fget(x) for x in tri["B"]]
    for i, (x, v) in enumerate(zip(tri["B"], vals)):
        hatch = "///" if x[4] else None
        ax.bar(i, v, width=0.68, color=x[3] if x[3] != "none" else SURF, edgecolor=x[4] or x[3], hatch=hatch, linewidth=1.5)
        rel = 100 * (v / vals[0] - 1)
        ax.text(i, v * 1.02, fmt(v) + ("" if i == 0 else f"\n{'+' if rel > 0 else ''}{fr(rel, 0)} %"), ha="center", va="bottom",
                fontsize=12, fontweight="bold" if i == 2 else "normal", color=INK)
    ax.set_xticks(range(4), ["Round-Robin\n3 VMs\ndédiées", "Optimiseur\n3 VMs\ndédiées", "Optimiseur\n1 dédiée +\n2 partagées",
                             "pareil,\npartagées\nà sec"], fontsize=10)
    ax.set_ylim(0, max(vals) * 1.32); ax.grid(axis="x", visible=False)
    ax.set_title(ttl, loc="left", fontweight="bold")
tB, cB = tri["B"], [x[2] for x in tri["B"]]
head(fig, f"Optimiser puis prendre des cœurs partagés : {fr(100 * (1 - tB[2][1] / tB[0][1]), 0)} % plus rapide et "
          f"{fr(100 * (1 - cB[2] / cB[0]), 0)} % moins cher que Round-Robin",
     f"Scénario B (10 tâches). Prédit par notre modèle avec les durées du jour ; le plan « opt + partagés » a été exécuté : "
     f"{fr(measB)} s mesurés.\nPrix GCP europe-west1 à la demande : e2-standard-2 0,0737 $/h, e2-medium 0,0369 $/h (payé à la seconde).")
save(fig, "oral_trio", top=0.77, bottom=0.16)

# ---------------------------------------------------------------------------------------------- rule
fig, axs = plt.subplots(1, 2, figsize=(13, 5.2), sharey=True)
# left: one job of L seconds of computation (2 busy vCPUs), medium starting with a full reserve
Ls = [x * 5 for x in range(1, 241)]          # 5 s .. 20 min of computation on an e2-standard-2
rat_job, rat_time = [], []
for L in Ls:
    W = std * L
    tb = TB
    t_med = W / b if W <= b * tb else tb + (W - b * tb) / base
    rat_job.append(100 * (PM * t_med) / (PS * L))
    rat_time.append(t_med / L)
axs[0].plot([L / 60 for L in Ls], [100] * len(Ls), color=BLUE, lw=2.2, ls="--")
axs[0].plot([L / 60 for L in Ls], rat_job, color=ORANGE, lw=2.8)
axs[0].axvspan(0, TB / 60, color=ORANGE_L, alpha=0.4, lw=0)
axs[0].text(TB / 60 + 0.3, 30, f"← job de moins de {fr(TB / 60, 0)} min :\n    moitié prix, même temps", ha="left", fontsize=11.5, fontweight="bold", color=INK)
axs[0].text(11, 63, "le surplus tourne à moitié vitesse :\nle prix remonte, le job s'allonge", fontsize=10.5, color=INK2)
axs[0].set_xlabel("durée du job sur une e2-standard-2 (minutes)")
axs[0].set_title("Un job, lancé après une pause", loc="left", fontweight="bold")
axs[0].set_xlim(0, 20)
# right: periodic load, busy a fraction u of the time
us = [i / 100 for i in range(1, 101)]
rat_u = []
for u in us:
    spd = b if u * 1 <= (1 - u) * rho else base + (1 - u) * rho * (b - base) / u
    rat_u.append(100 * (PM / spd) / (PS / std))
ustar = rho / (1 + rho)
axs[1].plot([100 * u for u in us], [100] * len(us), color=BLUE, lw=2.2, ls="--")
axs[1].plot([100 * u for u in us], rat_u, color=ORANGE, lw=2.8)
axs[1].axvspan(0, 100 * ustar, color=ORANGE_L, alpha=0.4, lw=0)
axs[1].text(100 * ustar / 2, 20, "burst permanent :\nmoitié prix", ha="center", fontsize=11.5, fontweight="bold", color=INK)
axs[1].text(100 * ustar + 3, 40, f"au-delà de ~50 % :\nde plus en plus\nlent et cher", fontsize=10.5, color=INK2, ha="left", va="top")
axs[1].set_xlabel("part du temps où la VM calcule (%)")
axs[1].set_title("Une VM qui calcule par intermittence", loc="left", fontweight="bold")
axs[1].set_xlim(0, 100)
axs[0].set_ylabel("prix du calcul (% du prix e2-standard-2)")
axs[0].set_ylim(0, 115)
for ax in axs:
    ax.text(ax.get_xlim()[1], 103, "e2-standard-2 ", color=BLUE, ha="right", fontsize=10.5)
head(fig, "Quand louer une e2-medium : jobs de moins de 2 min, ou VM occupée moins de la moitié du temps",
     "Prix du même calcul sur une e2-medium, en % de l'e2-standard-2 (modèle calé sur nos mesures). Jamais plus cher :\n"
     "au pire le même prix, mais 2× plus long. Si le délai compte et que la VM calcule sans arrêt, prendre l'e2-standard-2.")
save(fig, "oral_burst_rule", top=0.78)

json.dump({sc: [(l.replace("\n", " "), round(t, 2), round(c, 4)) for l, t, c, _, _ in tri[sc]] for sc in tri},
          open(os.path.join(OUT, "oral_trio.json"), "w"), indent=1, ensure_ascii=False)

# ---------------------------------------------------------------------------------------------- burst, 2nd experiment
# measure_p.sh ran the e2-medium runs back to back: the ratio medium / standard breaks at the burst reserve (D47)
raw = list(csv.DictReader(open(os.path.join(CS, "p_raw.csv"))))
stdt = {}
for r in raw:
    if r["vm"] == "cloudopt-vm1":
        stdt.setdefault((r["workload"], r["size"]), []).append(float(r["runtime_s"]))
cum, pts_in, pts_out = 0.0, [], []
for r in raw:
    if r["vm"] != "cloudopt-vm2":
        continue
    t = float(r["runtime_s"])
    ratio = t / st.mean(stdt[(r["workload"], r["size"])])
    (pts_in if cum + t <= TB else pts_out).append((cum, ratio))
    cum += t
fig, ax = plt.subplots(figsize=(11, 4.6))
ax.axvspan(0, TB, color=ORANGE_L, alpha=0.45, lw=0)
ax.scatter([x for x, _ in pts_in], [y for _, y in pts_in], s=60, color=BLUE, zorder=3, label="run dans la réserve")
ax.scatter([x for x, _ in pts_out], [y for _, y in pts_out], s=60, color=ORANGE, zorder=3, label="run après la réserve")
ax.axhline(1, color=INK3, lw=1, ls="--")
ax.axvline(TB, color=INK, lw=1.2)
ax.text(TB - 3, 2.65, f"réserve mesurée par l'étude burst : {fr(TB, 0)} s", fontsize=11.5, color=INK, va="top", ha="right")
ax.set_xlabel("temps de calcul cumulé sur l'e2-medium au début du run (s)")
ax.set_ylabel("durée e2-medium / durée e2-standard-2")
ax.set_ylim(0, 2.8); ax.legend(loc="center left", fontsize=11)
head(fig, "Deuxième expérience, même seuil : l'e2-medium ralentit après ~120 s de calcul cumulé",
     "Mesure des p_ij du 13/11 (tâches enchaînées sur l'e2-medium) : rapport ≈ 1 dans le burst, puis jusqu'à 2,5.")
save(fig, "oral_burst_confirm", top=0.80)
