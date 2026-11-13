#!/usr/bin/env python3
"""burst_cost.py — when is a shared-core e2-medium worth it? Time and money, from MEASURED burst parameters.
Usage: python3 scripts/burst_cost.py BURST_SESSION [COMPARE_SESSION]
  BURST_SESSION   results/burst/session_* (burst_params.json from burst_analysis.py)
  COMPARE_SESSION results/project/session_* (p_matrix_now.csv: p_ij measured the same day); default:
                  data/p_matrix_now.csv, else data/p_matrix.csv (TD2)
Prices: on-demand, europe-west1, USD per hour (gcloud-compute.com, Nov 2026): e2-standard-2 0.0737,
e2-medium 0.0369 (half), billed per second. Override with PRICE_STD2 / PRICE_MEDIUM.
Model of an e2-medium (a token bucket, parameters measured by burst_study.sh):
  while it has credits it runs at its burst speed b and spends credits at (b - base) per second;
  without credits it runs at its base speed; idle, it regains credits at r per second, up to C.
Writes results/fig_burst_cost.png, results/fig_burst_duty.png, results/fig_burst_fleet.png,
results/burst_study.md."""
import csv, json, math, os, re, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
B = sys.argv[1]
P = json.load(open(os.path.join(B, "burst_params.json")))["phases"]
PS, PM = float(os.environ.get("PRICE_STD2", 0.0737)), float(os.environ.get("PRICE_MEDIUM", 0.0369))


def ph(name, vm):
    return P.get(f"{name}|{vm}")


d2, d1, s2 = ph("deplete", "cloudopt-vm2"), ph("deplete", "cloudopt-vm3"), ph("deplete", "cloudopt-vm1")
s1 = next((v for k, v in P.items() if k.endswith("|cloudopt-vm1") and v["streams"] == 1), {"initial_speed": 1.0})
M = {2: {"b": d2["initial_speed"], "base": d2["final_speed"], "C": d2["credits_vcpu_s"] or 0.0},
     1: {"b": d1["initial_speed"], "base": d1["final_speed"], "C": d1["credits_vcpu_s"] or 0.0}}
STD = {2: s2["initial_speed"], 1: s1["initial_speed"]}
# recharge rate r: credits regained after an idle period, below the cap (2 streams, vm2)
rec = sorted((int(k.split("|")[0].split("_")[1]), v) for k, v in P.items() if k.startswith("recover_") and k.endswith("|cloudopt-vm2"))
pts = [(idle, v["credits_vcpu_s"]) for idle, v in rec if v["credits_vcpu_s"] is not None and not v["held_whole_probe"]
       and v["credits_vcpu_s"] < 0.9 * M[2]["C"]]
r = sum(c for _, c in pts) / sum(i for i, _ in pts) if pts else float("nan")


def t_medium(W, k, credits):
    """time to do W full-speed vCPU-seconds of work with k busy vCPUs, starting with `credits`."""
    m = M[k]
    drain = max(m["b"] - m["base"], 1e-9)
    tb = credits / drain                    # how long the burst lasts
    if W <= m["b"] * tb:
        return W / m["b"]
    return tb + (W - m["b"] * tb) / m["base"]


import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
BLUE, ORANGE, AQUA, GRAY, INK, INK2, GRID = "#2a78d6", "#eb6834", "#1baf7a", "#9a9890", "#0b0b0b", "#52514e", "#e6e5e0"
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
                     "grid.color": GRID, "axes.axisbelow": True, "legend.frameon": False})

# 1. one job of W work-seconds, both vCPUs busy: time and cost
Ws = [10 ** (x / 20) for x in range(0, 81)]          # 1 s .. 10^4 s of work
k = 2
ts = [W / STD[k] for W in Ws]
tf = [t_medium(W, k, M[k]["C"]) for W in Ws]
te = [t_medium(W, k, 0.0) for W in Ws]
cost = lambda t, p: 100 * p * t / 3600              # cents
fig, (a, b) = plt.subplots(1, 2, figsize=(11, 3.9))
for ys, lab, col, ls in [(ts, "e2-standard-2", BLUE, "-"), (tf, "e2-medium, crédits pleins", ORANGE, "-"),
                         (te, "e2-medium, sans crédits", ORANGE, "--")]:
    a.plot(Ws, [y / x for x, y in zip(Ws, ys)], color=col, lw=2, ls=ls, label=lab)
    p = PS if col == BLUE else PM
    b.plot(Ws, [cost(y, p) / x * 1000 for x, y in zip(Ws, ys)], color=col, lw=2, ls=ls, label=lab)
Wb = M[k]["b"] * M[k]["C"] / max(M[k]["b"] - M[k]["base"], 1e-9)
for ax in (a, b):
    ax.set_xscale("log"); ax.set_xlabel("taille du job (secondes de travail à pleine vitesse, 2 vCPU)")
    ax.axvline(Wb, color=INK2, lw=1, ls=":")
a.text(Wb * 1.1, a.get_ylim()[1] * 0.92, f"fin des crédits\n≈ {Wb:.0f} s de travail", fontsize=8, color=INK2)
a.set_ylabel("temps / travail (s par s de travail)"); a.set_title("Vitesse : identique tant qu'il reste des crédits")
b.set_ylabel("coût pour 1000 s de travail (cents $)"); b.set_title("Coût : l'e2-medium coûte moitié moins en burst")
a.legend(fontsize=8)
fig.tight_layout(); fig.savefig("results/fig_burst_cost.png", dpi=150); plt.close(fig)

# 2. periodic workload: busy a fraction u of the time (2 vCPUs), idle the rest
us = [i / 100 for i in range(2, 101)]
drain = M[2]["b"] - M[2]["base"]


def medium_speed(u):
    if math.isnan(r):
        return float("nan")
    if u * drain <= (1 - u) * r:                     # credits earned while idle cover the burst
        return M[2]["b"]
    return M[2]["base"] + (1 - u) * r / u           # what is earned while idle is spent while busy
spd = [medium_speed(u) for u in us]
ustar = r / (r + drain) if not math.isnan(r) else float("nan")
fig, (a, b) = plt.subplots(1, 2, figsize=(11, 3.9))
a.plot([100 * u for u in us], [STD[2]] * len(us), color=BLUE, lw=2, label="e2-standard-2")
a.plot([100 * u for u in us], spd, color=ORANGE, lw=2, label="e2-medium")
b.plot([100 * u for u in us], [1000 * 100 * PS / 3600 / STD[2]] * len(us), color=BLUE, lw=2, label="e2-standard-2")
b.plot([100 * u for u in us], [1000 * 100 * PM / 3600 / x for x in spd], color=ORANGE, lw=2, label="e2-medium")
for ax in (a, b):
    ax.set_xlabel("taux d'occupation de la VM (% du temps où elle calcule)")
    if not math.isnan(ustar):
        ax.axvline(100 * ustar, color=INK2, lw=1, ls=":")
a.set_ylabel("vitesse pendant le calcul (vCPU)"); a.set_title("Vitesse obtenue selon l'occupation")
b.set_ylabel("coût pour 1000 s de travail (cents $)"); b.set_title("Coût par travail utile (VM payée tout le temps)")
if not math.isnan(ustar):
    a.text(100 * ustar + 1, a.get_ylim()[0] + 0.1, f"≤ {100 * ustar:.0f} % : burst permanent", fontsize=8, color=INK2)
a.legend(fontsize=8)
fig.tight_layout(); fig.savefig("results/fig_burst_duty.png", dpi=150); plt.close(fig)

# 3. fleets for our batches: which VMs to rent? predicted makespan vs cost of one batch
cs = sys.argv[2] if len(sys.argv) > 2 else None
pfile = os.path.join(cs, "p_matrix_now.csv") if cs else ("data/p_matrix_now.csv" if os.path.exists("data/p_matrix_now.csv") else "data/p_matrix.csv")
cols = next(csv.reader(open(pfile)))
std_col = "gce_std2_now" if "gce_std2_now" in cols else "cloud_vm1_std2"
med_col = "gce_medium_now" if "gce_medium_now" in cols else "cloud_vm1_std2"
rows = list(csv.DictReader(open(pfile)))
tmp = tempfile.mkdtemp()
pf = os.path.join(tmp, "p.csv")
with open(pf, "w") as f:                               # medium without credits: measured burst p scaled by b/base
    f.write("task,std2,med_burst,med_empty\n")
    for rr in rows:
        mb = float(rr[med_col])
        f.write(f"{rr['task']},{rr[std_col]},{mb},{mb * M[2]['b'] / M[2]['base']}\n")
FLEETS = [(3, 0), (2, 0), (1, 0), (2, 1), (1, 2), (1, 1), (0, 3), (0, 2), (0, 4), (0, 6)]


def solve(tasks, n_std, n_med, col):
    vf = os.path.join(tmp, f"v_{n_std}_{n_med}_{col}.csv")
    with open(vf, "w") as f:
        f.write("vm,machine_type,ram_mb,p_column,eff_cores\n")
        for i in range(n_std):
            f.write(f"cloudopt-s{i+1},e2-standard-2,8192,std2,1.25\n")
        for i in range(n_med):
            f.write(f"cloudopt-m{i+1},e2-medium,4096,{col},1.25\n")
    out = subprocess.run(["bin/optimizer", "-tasks", tasks, "-vms", vf, "-p", pf, "-max-per-vm", "10"],
                         capture_output=True, text=True).stdout
    m = re.search(r"makespan=([0-9.]+)", out)
    if not m:
        return None, None
    work = {}
    for line in out.splitlines():
        if line.startswith("cloudopt-m"):
            work[line.split()[0]] = float(line.split()[3])
    return float(m.group(1)), work


res = []
for name, tasks in [("A", "data/tasks.csv"), ("B", "data/tasks_b.csv")]:
    for n_std, n_med in FLEETS:
        ms, work = solve(tasks, n_std, n_med, "med_burst")
        if ms is None:
            continue
        burst_ok = all(w <= M[2]["b"] * M[2]["C"] / max(drain, 1e-9) for w in work.values())   # credits suffice?
        if not burst_ok:
            ms, _ = solve(tasks, n_std, n_med, "med_empty")
        price = n_std * PS + n_med * PM
        res.append((name, n_std, n_med, ms, 100 * price * ms / 3600, burst_ok, price))
fig, axs = plt.subplots(1, 2, figsize=(11, 4))
for ax, sc in zip(axs, ["A", "B"]):
    pts_ = [x for x in res if x[0] == sc]
    front = [p for p in pts_ if not any((q[3] <= p[3] and q[4] < p[4]) or (q[3] < p[3] and q[4] <= p[4]) for q in pts_)]
    for p in pts_:
        col = BLUE if p in front else GRAY
        ax.scatter(p[3], p[4], s=50, color=col, edgecolor="white", linewidth=1.5, zorder=3)
        ax.annotate(f"{p[1]}×std2 + {p[2]}×med" + ("" if p[5] or p[2] == 0 else " (sans crédits)"), (p[3], p[4]),
                    textcoords="offset points", xytext=(5, 4), fontsize=7.5, color=INK if p in front else INK2)
    fr = sorted(front, key=lambda p: p[3])
    ax.plot([p[3] for p in fr], [p[4] for p in fr], color=BLUE, lw=1.2, zorder=2)
    ax.set_xlabel("makespan prédit (s)"); ax.set_ylabel("coût du lot (cents $)")
    ax.set_title(f"Scénario {sc} : quelles VMs louer ? (bleu = front de Pareto)")
fig.tight_layout(); fig.savefig("results/fig_burst_fleet.png", dpi=150); plt.close(fig)

L = ["# Cœurs partagés (e2-medium) : quand utiliser le burst ? (`scripts/burst_cost.py`)", "",
     f"Paramètres mesurés ({os.path.basename(B)}) : burst à {M[2]['b']:.2f} vCPU (2 vCPU occupés), régime de base {M[2]['base']:.2f} vCPU, "
     f"réserve de crédits ≈ {M[2]['C']:.0f} vCPU·s, recharge ≈ {r:.2f} vCPU·s par seconde d'inactivité ; e2-standard-2 : {STD[2]:.2f} vCPU (2 occupés), {STD[1]:.2f} (1 occupé).",
     f"Prix (europe-west1, à la demande, $/h) : e2-standard-2 {PS}, e2-medium {PM}.", "",
     "## Règle de décision", "",
     f"- Job court : tant que le travail tient dans les crédits (≈ {Wb:.0f} s de travail à 2 vCPU), l'e2-medium va aussi vite que l'e2-standard-2 pour **{100 * PM / PS:.0f} % du prix**.",
     f"- Charge intermittente : si la VM calcule moins de **{100 * ustar:.0f} %** du temps, les crédits regagnés pendant les pauses suffisent : burst permanent." if not math.isnan(ustar) else "- Recharge non mesurée.",
     f"- Charge continue : l'e2-medium retombe à {M[2]['base']:.2f} vCPU ; coût par travail = {100 * (PM / M[2]['base']) / (PS / STD[2]):.0f} % de celui de l'e2-standard-2, mais en {STD[2] / M[2]['base']:.1f}× plus de temps.", "",
     "## Quelles VMs louer pour nos lots (prédit)", "", "| lot | flotte | prix ($/h) | crédits suffisants | makespan (s) | coût du lot (cents $) |", "|---|---|---:|---|---:|---:|"]
for x in res:
    L.append(f"| {x[0]} | {x[1]} × e2-standard-2 + {x[2]} × e2-medium | {x[6]:.4f} | {'oui' if x[5] or x[2] == 0 else 'non'} | {x[3]:.1f} | {x[4]:.4f} |")
open("results/burst_study.md", "w").write("\n".join(L) + "\n")
print("\n".join(L))
print("written: results/fig_burst_cost.png, fig_burst_duty.png, fig_burst_fleet.png, results/burst_study.md")
