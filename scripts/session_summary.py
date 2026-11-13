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


def predicted(name):
    out = subprocess.run([os.path.join(ROOT, "bin/optimizer"), "-method", "eval", "-p", os.path.join(S, "p_matrix_now.csv"),
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
          "Plateforme : voir `platform.txt` ; p_ij du jour : `p_matrix_now.csv`."]
text = "\n".join(lines) + "\n"
open(os.path.join(S, "summary.md"), "w").write(text)
print(text)
