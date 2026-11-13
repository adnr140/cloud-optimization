#!/usr/bin/env python3
"""correct_medium_p.py — repair the e2-medium column of a session measured before the fix of measure_p.sh.
Usage: python3 scripts/correct_medium_p.py results/project/session_<date> [BURST_RESERVE_S]
Why: measure_p.sh ran the 24 runs back to back on the e2-medium. After ~120 s of continuous computation
its burst reserve is empty (measured independently by burst_study.sh: 122 s) and it runs at half speed,
so the last tasks of the loop (memory 2048, every sort) were measured 2x too slow. During the real runs the
e2-medium had rested, so it was in burst. Here: a run whose cumulative start time exceeds the reserve is
replaced by the e2-standard-2 time of the same task (in burst both VMs run at the same speed: the 16 runs
inside the burst agree within 2 %). Writes SESSION/p_matrix_now_corrected.csv and SESSION/vms_now_corrected.csv."""
import csv, glob, json, os, statistics as st, sys

S = sys.argv[1]
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if len(sys.argv) > 2:
    reserve = float(sys.argv[2])
else:
    bp = sorted(glob.glob(os.path.join(ROOT, "results/burst/session_*/burst_params.json")))[-1]
    reserve = json.load(open(bp))["phases"]["deplete|cloudopt-vm2"]["burst_s"]
raw = list(csv.DictReader(open(os.path.join(S, "p_raw.csv"))))
med = [r for r in raw if r["vm"] == "cloudopt-vm2"]
std = {}
for r in raw:
    if r["vm"] == "cloudopt-vm1":
        std.setdefault(f"{r['workload']}:{r['size']}", []).append(float(r["runtime_s"]))
cum, keep, ratios = 0.0, {}, []
for r in med:
    k = f"{r['workload']}:{r['size']}"
    t = float(r["runtime_s"])
    if cum + t <= reserve:                      # the whole run happened inside the burst
        keep.setdefault(k, []).append(t)
        ratios.append(t / st.mean(std[k]))
    cum += t
rows = list(csv.DictReader(open(os.path.join(S, "p_matrix_now.csv"))))
with open(os.path.join(S, "p_matrix_now_corrected.csv"), "w") as f:
    f.write("task,gce_std2_now,gce_medium_now\n")
    for r in rows:
        k = r["task"]
        m = st.mean(keep[k]) if k in keep else float(r["gce_std2_now"])
        f.write(f"{k},{r['gce_std2_now']},{m:.3f}\n")
open(os.path.join(S, "vms_now_corrected.csv"), "w").write(open(os.path.join(S, "vms_now.csv")).read())
print(f"reserve {reserve:.0f} s: {sum(len(v) for v in keep.values())}/{len(med)} e2-medium runs inside the burst, "
      f"medium/std2 ratio there = {st.mean(ratios):.3f}; tasks replaced by the e2-standard-2 time: "
      + ", ".join(r["task"] for r in rows if r["task"] not in keep))
