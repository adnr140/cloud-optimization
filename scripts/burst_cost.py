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
# recharge: rho = seconds of burst regained per second of rest, from the probes that ran out of credits
# before their end (the others only give a lower bound). The 1-vCPU probes are used for both cases
# (per-vCPU accounting; the 2-vCPU probes all held the whole probe, so they only say "at least").
def probes(vm, k):
    out = []
    for key, v in P.items():
        ph_, vm_ = key.split("|")
        if ph_.startswith("recover_") and vm_ == vm and v["credits_vcpu_s"] is not None:
            idle = int(ph_.split("_")[1])
            tb = v["credits_vcpu_s"] / max(M[k]["b"] - M[k]["base"], 1e-9)       # burst seconds regained
            out.append((idle, tb, v["held_whole_probe"]))
    return sorted(out)
PR = {1: probes("cloudopt-vm3", 1), 2: probes("cloudopt-vm2", 2)}
exact = [tb / idle for k in (1, 2) for idle, tb, held in PR[k] if not held and tb < 0.9 * M[k]["C"] / (M[k]["b"] - M[k]["base"])]
rho = sum(exact) / len(exact) if exact else float("nan")
rho_low = {k: max((tb / idle for idle, tb, held in PR[k] if held), default=None) for k in (1, 2)}
r = rho * (M[2]["b"] - M[2]["base"])        # credits (vCPU·s) regained per idle second, 2 vCPUs busy
TB = {k: M[k]["C"] / max(M[k]["b"] - M[k]["base"], 1e-9) for k in (1, 2)}   # burst length with full credits (s)


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
FLEETS = [(3, 0), (2, 0), (1, 0), (2, 1), (1, 2), (1, 1), (0, 3), (0, 2)]   # (e2-standard-2, e2-medium)


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
            work[line.split()[0]] = float(line.split()[6])   # finish_s
    return float(m.group(1)), work


res = []
for name, tasks in [("A", "data/tasks.csv"), ("B", "data/tasks_b.csv")]:
    for n_std, n_med in FLEETS:
        price = n_std * PS + n_med * PM
        ms, fin = solve(tasks, n_std, n_med, "med_burst")
        if ms is None:
            continue
        ok = all(f <= TB[2] for f in fin.values())                  # every medium finishes inside its burst
        if not ok:
            ms, _ = solve(tasks, n_std, n_med, "med_empty")
        res.append((name, n_std, n_med, ms, 100 * price * ms / 3600, "full", price))
        if n_med:                                                   # same fleet, mediums already out of credits
            me, _ = solve(tasks, n_std, n_med, "med_empty")
            if me is not None:
                res.append((name, n_std, n_med, me, 100 * price * me / 3600, "empty", price))
fig, axs = plt.subplots(1, 2, figsize=(11.5, 4.6))
OFF = {"A": {(3, 0): (6, 3), (2, 0): (6, -11), (1, 0): (-8, 6), (2, 1): (6, 3), (1, 2): (6, -12), (1, 1): (6, -11),
              (0, 3): (7, 3), (0, 2): (6, 4)},
       "B": {(3, 0): (6, 3), (2, 0): (6, 5), (1, 0): (-8, 6), (2, 1): (6, 3), (1, 2): (6, -13), (1, 1): (6, 6),
              (0, 3): (6, -12), (0, 2): (6, 4)}}
for ax, sc in zip(axs, ["A", "B"]):
    pts_ = [x for x in res if x[0] == sc and x[5] == "full"]
    front = [p for p in pts_ if not any((q[3] <= p[3] and q[4] < p[4]) or (q[3] < p[3] and q[4] <= p[4]) for q in pts_)]
    for p in [x for x in res if x[0] == sc and x[5] == "empty"]:
        full = next(q for q in pts_ if q[1:3] == p[1:3])
        ax.annotate("", (p[3], p[4]), (full[3], full[4]),
                    arrowprops=dict(arrowstyle="-", color=ORANGE, lw=0.8, alpha=0.45, shrinkA=4, shrinkB=4))
        ax.scatter(p[3], p[4], s=30, facecolor="white", edgecolor=ORANGE, linewidth=1.2, zorder=3)
    fr = sorted(front, key=lambda p: p[3])
    ax.plot([p[3] for p in fr], [p[4] for p in fr], color=BLUE, lw=1.2, zorder=2)
    for p in pts_:
        col = BLUE if p in front else GRAY
        ax.scatter(p[3], p[4], s=55, color=col, edgecolor="white", linewidth=1.5, zorder=4)
        if p[1:3] == (1, 2):
            ax.scatter(p[3], p[4], s=170, facecolor="none", edgecolor=INK, linewidth=1, zorder=4)
        lab = " + ".join(t for t in (f"{p[1]} std2" if p[1] else "", f"{p[2]} medium" if p[2] else "") if t)
        dx, dy = OFF[sc].get(p[1:3], (6, 4))
        ax.annotate(lab + (" (notre flotte)" if p[1:3] == (1, 2) else ""), (p[3], p[4]), textcoords="offset points",
                    xytext=(dx, dy), ha="right" if dx < 0 else "left", fontsize=8, color=INK if p in front else INK2, zorder=5)
    ax.set_xlabel("makespan prédit (s)"); ax.set_ylabel("coût du lot (cents $)")
    ax.set_title(f"Scénario {sc} : quelles VMs louer ?")
axs[0].scatter([], [], s=55, color=BLUE, label="e2-medium avec crédits : front de Pareto")
axs[0].scatter([], [], s=55, color=GRAY, label="e2-medium avec crédits : dominé")
axs[0].scatter([], [], s=30, facecolor="white", edgecolor=ORANGE, label="même flotte, e2-medium à sec")
axs[0].legend(fontsize=7.5, loc="upper right")
fig.tight_layout(); fig.savefig("results/fig_burst_fleet.png", dpi=150); plt.close(fig)

lowtxt = ", ".join(f"{k} vCPU : ≥ {v:.1f}" for k, v in rho_low.items() if v)
L = ["# Cœurs partagés (e2-medium) : quand utiliser le burst ? (`scripts/burst_cost.py`)", "",
     f"Mesuré ({os.path.basename(B)}), en « vCPU à pleine vitesse » (1 = un fil seul sur un cœur libre) :", "",
     "| | e2-standard-2 | e2-medium en burst | e2-medium sans crédits |", "|---|---:|---:|---:|",
     f"| 2 vCPU occupés | {STD[2]:.2f} | {M[2]['b']:.2f} | {M[2]['base']:.2f} |",
     f"| 1 vCPU occupé | {STD[1]:.2f} | {M[1]['b']:.2f} | {M[1]['base']:.2f} |",
     f"| prix ($/h, europe-west1, à la demande) | {PS} | {PM} | {PM} |",
     f"| vitesse par $/h (2 vCPU) | {STD[2] / PS:.1f} | {M[2]['b'] / PM:.1f} | {M[2]['base'] / PM:.1f} |", "",
     f"- Réserve après 10 min de repos : burst tenu {TB[2]:.0f} s (2 vCPU) et {TB[1]:.0f} s (1 vCPU), soit {M[2]['C']:.0f} et {M[1]['C']:.0f} vCPU·s au-dessus du régime de base.",
     f"- Recharge : {rho:.2f} s de burst regagnée par seconde de repos (sondes qui ont épuisé leurs crédits) ; "
     f"les sondes qui ont tenu jusqu'au bout donnent seulement un minimum ({lowtxt}). Le modèle prend la valeur prudente {rho:.2f}.", "",
     "## Règle de décision", "",
     f"- Job court : tant que le travail tient dans le burst (≈ {Wb:.0f} s de travail à 2 vCPU, {TB[2]:.0f} s de calcul), l'e2-medium va aussi vite que l'e2-standard-2 pour **{100 * PM / PS:.0f} % du prix**.",
     f"- Charge intermittente : si la VM calcule moins de **{100 * ustar:.0f} %** du temps, ce qu'elle regagne pendant les pauses couvre le burst : pleine vitesse en permanence." if not math.isnan(ustar) else "- Recharge non mesurée.",
     f"- Charge continue : l'e2-medium retombe à {M[2]['base']:.2f} vCPU. Le coût par travail reste {100 * (PM / M[2]['base']) / (PS / STD[2]):.0f} % de celui de l'e2-standard-2 (moitié de vitesse pour moitié de prix), mais c'est {STD[2] / M[2]['base']:.1f}× plus long.", "",
     "## Quelles VMs louer pour nos lots (prédit par l'optimiseur, p_ij du jour)", "",
     "| lot | flotte | prix ($/h) | e2-medium | makespan (s) | coût du lot (cents $) |", "|---|---|---:|---|---:|---:|"]
for x in res:
    L.append(f"| {x[0]} | {x[1]} × e2-standard-2 + {x[2]} × e2-medium | {x[6]:.4f} | "
             f"{'—' if x[2] == 0 else ('crédits pleins' if x[5] == 'full' else 'sans crédits')} | {x[3]:.1f} | {x[4]:.4f} |")
open("results/burst_study.md", "w").write("\n".join(L) + "\n")
print("\n".join(L))
print("written: results/fig_burst_cost.png, fig_burst_duty.png, fig_burst_fleet.png, results/burst_study.md")
