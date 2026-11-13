#!/usr/bin/env python3
"""bruteforce_check.py — INDEPENDENT check of bin/optimizer -method exact.

Usage: python3 scripts/bruteforce_check.py TASKS_CSV [VMS_CSV]
Enumerates ALL M^N plans with plain itertools (no pruning, no shared code with the Go program),
same model (processor sharing, SSH, RAM - reserve, max tasks per VM) and prints the best makespan.
test_optimizer.sh compares it with the Go result: two different programs must find the same optimum.
"""
import csv, itertools, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SSH, RESERVE, MAXPER = 3.0, 512.0, 10


def main():
    tasks = list(csv.DictReader(open(sys.argv[1])))
    vms = list(csv.DictReader(open(sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "data/vms.csv"))))
    P = {r["task"]: r for r in csv.DictReader(open(os.path.join(ROOT, "data/p_matrix.csv")))}
    R = {f'{r["workload"]}:{r["size"]}': float(r["max_max_rss_kb"]) / 1024
         for r in csv.DictReader(open(os.path.join(ROOT, "data/workload_profile_cloud_vm1_std2.csv")))}
    keys = [f'{t["workload"]}:{t["size"]}' for t in tasks]

    def finish(ps, c):
        if not ps:
            return 0.0
        t = done = 0.0
        ps = sorted(ps)
        for k, w in enumerate(ps):
            t += (w - done) / min(1.0, c / (len(ps) - k))
            done = w
        return SSH + t

    best = None
    for plan in itertools.product(range(len(vms)), repeat=len(tasks)):
        fins = []
        for j, v in enumerate(vms):
            mine = [k for k, a in zip(keys, plan) if a == j]
            if len(mine) > MAXPER or sum(R[k] for k in mine) > float(v["ram_mb"]) - RESERVE:
                break
            fins.append(finish([float(P[k][v["p_column"]]) for k in mine], float(v["eff_cores"])))
        else:
            m = max(fins)
            if best is None or m < best:
                best = m
    print("infeasible" if best is None else f"{best:.1f}")


if __name__ == "__main__":
    main()
