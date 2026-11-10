"""plot_machines.py — TD2 figure: same tasks on 3 machines + per-pass behaviour (burst on shared core).
Usage: python3 scripts/plot_machines.py results/  (reads data/benchmark_{local,cloud_vm1,cloud_vm1_std2}.csv)"""
import csv, sys, statistics as st
from collections import defaultdict
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

out = sys.argv[1] if len(sys.argv) > 1 else "results"
machines = [("local", "laptop Ryzen 7 7840HS (WSL2)", "#4C72B0"),
            ("cloud_vm1", "GCP e2-medium (shared core)", "#DD8452"),
            ("cloud_vm1_std2", "GCP e2-standard-2", "#55A868")]
data = {}
for tag, _, _ in machines:
    d = defaultdict(dict)
    with open(f"data/benchmark_{tag}.csv") as f:
        for r in csv.DictReader(f):
            d[(r["workload"], int(r["size"]))][int(r["run"])] = float(r["runtime_s"])
    data[tag] = d
configs = sorted(data["local"], key=lambda k: (k[0], k[1]))
short = {"cpu_task": "cpu", "memory_task": "mem", "matrix_task": "matrix", "sort_task": "sort"}
labels = [f"{short[w]}\n{s:,}".replace(",", " ") for w, s in configs]

fig, (a, b) = plt.subplots(2, 1, figsize=(13, 9), gridspec_kw={"height_ratios": [3, 2]})
wdt = 0.27
for m, (tag, name, col) in enumerate(machines):
    xs = [i + (m - 1) * wdt for i in range(len(configs))]
    runs = [list(data[tag][k].values()) for k in configs]
    mean = [st.mean(r) for r in runs]
    a.bar(xs, mean, wdt, label=name, color=col,
          yerr=[[mu - min(r) for mu, r in zip(mean, runs)], [max(r) - mu for mu, r in zip(mean, runs)]], capsize=2)
a.set_xticks(range(len(configs))); a.set_xticklabels(labels, fontsize=8)
a.set_yscale("log"); a.set_ylabel("mean wall time (s, log)  —  bars = min–max of 3 runs")
a.set_title("Same binaries, same sizes, 3 machines: the slowdown depends on the task (unrelated machines, p_ij)")
a.legend(); a.grid(axis="y", alpha=.3)

for tag, name, col in machines[1:]:
    for s, ls in [(5000000, ":"), (10000000, "--"), (20000000, "-")]:
        r = data[tag][("cpu_task", s)]
        b.plot(sorted(r), [r[k] for k in sorted(r)], ls, marker="o", color=col, label=f"{name} — cpu_task {s//1000000}M")
b.set_xticks([1, 2, 3]); b.set_xlabel("pass (runs interleaved: pass 1 = every config once, then pass 2...)")
b.set_ylabel("wall time (s)"); b.grid(alpha=.3); b.legend(fontsize=7, ncol=2)
b.set_title("Shared core: pass 1 runs at full speed on burst credits, then ~2× slower. Dedicated core: flat.")
fig.tight_layout(); fig.savefig(f"{out}/td2_machines.png", dpi=130)
print(f"written: {out}/td2_machines.png")
