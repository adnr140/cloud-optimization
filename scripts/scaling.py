#!/usr/bin/env python3
"""scaling.py — how the methods of bin/optimizer behave when the problem grows (no VM needed).

Usage: python3 scripts/scaling.py            (writes results/scaling.md and results/scaling.csv)

Random instances are built ONLY from measured (workload, size) pairs of data/p_matrix.csv.
Fleet: 1 e2-standard-2 for 2 e2-medium, like ours. The e2-medium use the column of their own type
(cloud_vm1: credits exhausted, long runs) so that the machines are really heterogeneous (R||Cmax),
the hard case of CM3. c = 1.25 effective cores everywhere (results/model_fit.md).
Part 1 (quality): small instances, every method compared with the proved optimum (exact, OPTIMAL).
Part 2 (scale): from 9 to 1000 tasks, about 5 tasks per VM (RAM and sshd limit, D24):
computation time and gap to the lower bound (CM4: plan U, bound L, gap U-L).
"""
import csv, os, random, re, subprocess, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "bin/optimizer")
KEYS = [r["task"] for r in csv.DictReader(open(os.path.join(ROOT, "data/p_matrix.csv")))]
TMP = tempfile.mkdtemp()


def instance(n, m, seed):
    rnd = random.Random(seed)
    t = os.path.join(TMP, f"t_{n}_{m}_{seed}.csv")
    v = os.path.join(TMP, f"v_{m}.csv")
    with open(t, "w") as f:
        f.write("task_id,workload,size\n")
        for i in range(n):
            w, s = rnd.choice(KEYS).split(":")
            f.write(f"X{i+1},{w},{s}\n")
    with open(v, "w") as f:
        f.write("vm,machine_type,ram_mb,p_column,eff_cores\n")
        for j in range(m):
            std = j % 3 == 0
            f.write(f"vm{j+1},{'e2-standard-2' if std else 'e2-medium'},{8192 if std else 4096},"
                    f"{'cloud_vm1_std2' if std else 'cloud_vm1'},1.25\n")
    return t, v


def solve(method, t, v, limit=10):
    out = subprocess.run([BIN, "-method", method, "-tasks", t, "-vms", v, "-time-limit", str(limit)],
                         capture_output=True, text=True, cwd=ROOT)
    s = re.search(r"^summary (.*)$", out.stdout, re.M)
    if not s:
        return None
    d = dict(kv.split("=") for kv in s.group(1).split())
    return {k: (float(x) if k not in ("method", "status") else x) for k, x in d.items()}


METHODS = ["rr", "lpt", "minmin", "maxmin", "greedy", "ls", "ils"]
rows, lines = [], []

# ---- part 1: quality against the proved optimum
lines += ["# Passage à l'échelle des méthodes (`scripts/scaling.py`)", "",
          "Instances aléatoires tirées des 12 tâches mesurées (`data/p_matrix.csv`). Parc : 1 e2-standard-2 pour 2 e2-medium,",
          "les e2-medium avec leur propre colonne (crédits épuisés) pour que les machines soient vraiment hétérogènes.", "",
          "## 1. Qualité : écart à l'optimum prouvé (petites instances)", ""]
gaps = {k: [] for k in METHODS}
hits = {k: 0 for k in METHODS}
count = 0
for n, m in [(8, 3), (10, 3), (12, 3), (12, 4)]:
    for seed in range(10):
        t, v = instance(n, m, 1000 * n + 10 * m + seed)
        ex = solve("opt", t, v, limit=60)
        if ex is None or ex["status"] != "OPTIMAL":
            continue
        count += 1
        for k in METHODS:
            r = solve(k, t, v)
            if r is None:  # infeasible plan (RAM): count it as a failure
                gaps[k].append(None)
                continue
            g = 100 * (r["makespan"] - ex["makespan"]) / ex["makespan"]
            gaps[k].append(g)
            hits[k] += g < 1e-6
            rows.append({"part": "quality", "tasks": n, "vms": m, "seed": seed, "method": k,
                         "makespan": r["makespan"], "optimum": ex["makespan"], "gap_to_opt_pct": round(g, 3)})
lines += [f"{count} instances (8 à 12 tâches, 3 ou 4 VMs), chacune résolue à l'optimum par la recherche exacte.", "",
          "| méthode | optimum trouvé | écart moyen à l'optimum | écart max | plan infaisable (RAM) |",
          "|---|---:|---:|---:|---:|"]
names = {"rr": "Round-Robin (baseline)", "lpt": "LPT", "minmin": "Min-Min", "maxmin": "Max-Min",
         "greedy": "meilleur des 3 (LPT, Min-Min, Max-Min)", "ls": "+ recherche locale (descente)",
         "ils": "**+ recherche locale itérée**"}
for k in METHODS:
    ok = [g for g in gaps[k] if g is not None]
    bad = len(gaps[k]) - len(ok)
    lines.append(f"| {names[k]} | {hits[k]}/{len(ok)} | {sum(ok)/len(ok):.2f} % | {max(ok):.2f} % | {bad} |" if ok
                 else f"| {names[k]} | — | — | — | {bad} |")

# ---- part 2: scale
lines += ["", "## 2. Passage à l'échelle : temps de calcul et écart à la borne inférieure", "",
          "Environ 5 tâches par VM. Écart = (plan − borne inférieure) / borne : c'est un **majorant** de l'écart à l'optimum",
          "(la borne peut être loin de l'optimum, l'écart réel est souvent plus petit). Méthode `opt` limitée à 10 s :",
          "au-delà elle rend le meilleur plan trouvé (FEASIBLE), comme un solveur. Moyenne de 3 instances par taille.", "",
          "| tâches | VMs | plans possibles | Round-Robin | meilleur glouton | + descente | + recherche itérée | `opt` | `opt` : statut | `opt` : temps max |",
          "|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|"]
import math
for n, m in [(9, 3), (20, 4), (50, 10), (100, 20), (200, 40), (500, 100), (1000, 200)]:
    res = {k: [] for k in ["rr", "greedy", "ls", "ils", "opt"]}
    for seed in range(3):
        t, v = instance(n, m, 7 * n + seed)
        for k in res:
            r = solve(k, t, v)
            rows.append({"part": "scale", "tasks": n, "vms": m, "seed": seed, "method": k,
                         **({"makespan": r["makespan"], "lower_bound": r["lower_bound"], "gap_to_lb_pct": r["gap_pct"],
                             "status": r["status"], "time_ms": r["time_ms"]} if r else {"status": "INFEASIBLE"})})
            if r:
                res[k].append(r)

    def g(k):
        if not res[k]:
            return "infaisable ×3"
        txt = f"{sum(r['gap_pct'] for r in res[k])/len(res[k]):.1f} %"
        return txt + (f" ({3-len(res[k])} infaisable{'s' if 3-len(res[k]) > 1 else ''})" if len(res[k]) < 3 else "")
    o = res["opt"]
    lines.append(f"| {n} | {m} | 10^{n * math.log10(m):.0f} | {g('rr')} | {g('greedy')} | {g('ls')} | {g('ils')} | {g('opt')} | "
                 f"{sum(r['status'] == 'OPTIMAL' for r in o)}/{len(o)} OPTIMAL | {max(r['time_ms'] for r in o)/1000:.2f} s |")
    print(lines[-1], flush=True)
lines += ["", "Lecture : les plans possibles explosent (M^N), le temps de calcul de `opt` reste borné par la limite.",
          "Un écart à la borne non nul avec le statut OPTIMAL (9 et 20 tâches) veut dire que la borne est loin : le plan est",
          "prouvé optimal par la recherche exacte, pas par la borne. Round-Robin devient infaisable dès 50 tâches (RAM).",
          "La preuve d'optimalité (OPTIMAL) s'obtient quand la recherche exacte termine (petites instances) ou quand le plan",
          "atteint la borne inférieure (grandes instances dominées par les plus grosses tâches)."]
open(os.path.join(ROOT, "results/scaling.md"), "w").write("\n".join(lines) + "\n")
with open(os.path.join(ROOT, "results/scaling.csv"), "w", newline="") as f:
    cols = ["part", "tasks", "vms", "seed", "method", "makespan", "optimum", "gap_to_opt_pct", "lower_bound",
            "gap_to_lb_pct", "status", "time_ms"]
    w = csv.DictWriter(f, fieldnames=cols)
    w.writeheader()
    w.writerows(rows)
print("\n".join(lines))
