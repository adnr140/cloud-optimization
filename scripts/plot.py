"""plot.py — optional figures from the raw CSV: input size vs mean runtime (error bars = min/max)
and input size vs mean max RSS. Usage: python3 scripts/plot.py data/benchmark_<tag>.csv results/ <tag>"""
import csv, sys, statistics as st
from collections import defaultdict
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

src, outdir = sys.argv[1], sys.argv[2]
tag = sys.argv[3] if len(sys.argv) > 3 else "local"
rt, rss = defaultdict(list), defaultdict(list)
with open(src) as f:
    for r in csv.DictReader(f):
        k = (r["workload"], int(r["size"]))
        rt[k].append(float(r["runtime_s"])); rss[k].append(int(r["max_rss_kb"]) / 1024)
workloads = sorted({w for w, _ in rt})
fig, axes = plt.subplots(2, len(workloads), figsize=(4.2 * len(workloads), 7), squeeze=False)
for j, w in enumerate(workloads):
    sizes = sorted(s for ww, s in rt if ww == w)
    m = [st.mean(rt[(w, s)]) for s in sizes]
    lo = [m[i] - min(rt[(w, s)]) for i, s in enumerate(sizes)]
    hi = [max(rt[(w, s)]) - m[i] for i, s in enumerate(sizes)]
    a = axes[0][j]; a.errorbar(sizes, m, yerr=[lo, hi], marker="o", capsize=4)
    a.set_title(w); a.set_xlabel("--size"); a.set_ylabel("mean runtime (s)"); a.grid(alpha=.3)
    b = axes[1][j]; b.plot(sizes, [st.mean(rss[(w, s)]) for s in sizes], marker="s", color="tab:orange")
    b.set_xlabel("--size"); b.set_ylabel("mean max RSS (MB)"); b.grid(alpha=.3)
fig.suptitle(f"{tag} benchmark — input size vs runtime / memory (3 runs, bars = min–max)")
fig.tight_layout(); fig.savefig(f"{outdir}/size_vs_runtime_rss_{tag}.png", dpi=130)
print(f"written: {outdir}/size_vs_runtime_rss_{tag}.png")
