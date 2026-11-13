#!/usr/bin/env python3
"""fit_model.py — calibrate the optimizer's duration model on REAL distributed runs.

Usage: python3 scripts/fit_model.py [RUN_DIR ...]   (default: every results/td3|td4 run with an allocation)
For every run and every VM: the tasks it ran and the MEASURED finish time (last end - first launch,
controller clock, SSH included). Then, for two hypotheses on p_ij, the effective core count c that
best predicts those finish times with a processor-sharing model (CM6: tasks on one VM share it):
    the VM has c effective cores; while n tasks run, each one advances at speed min(1, c/n);
    finish_j = SSH + the time at which the last task of VM j has done its p_ij seconds of work
  H1 "by type"   : e2-standard-2 uses its own TD2 column, e2-medium the e2-medium column
  H2 "same speed": every VM uses the e2-standard-2 column (e2 2-vCPU VMs = 1 physical core,
                   e2-medium bursting at full speed on short runs)
Prints the error of each (MAE, MAPE) and a leave-one-run-out check (fit on the other runs, predict
the run left out). Standard library only. Output -> results/model_fit.md
"""
import csv, glob, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = {r["task"]: r for r in csv.DictReader(open(os.path.join(ROOT, "data/p_matrix.csv")))}
TYPE = {"cloudopt-vm1": "cloud_vm1_std2", "cloudopt-vm2": "cloud_vm1", "cloudopt-vm3": "cloud_vm1"}
SKIP = {"allocation_failtest"}


def observations(run):
    alloc = list(csv.DictReader(open(os.path.join(run, "allocation.csv"))))
    meta = {}
    for f in glob.glob(os.path.join(run, "*.meta")):
        kv = dict(l.strip().split("=", 1) for l in open(f) if "=" in l)
        meta[kv["task_id"]] = kv
    t0 = min(float(m["launch_epoch"]) for m in meta.values())
    obs = []
    for vm in sorted({a["vm"] for a in alloc}):
        rows = [a for a in alloc if a["vm"] == vm]
        end = max(float(meta[a["task_id"]]["end_epoch"]) for a in rows)
        obs.append((os.path.relpath(run, ROOT), vm, [f'{a["workload"]}:{a["size"]}' for a in rows], end - t0))
    return obs


def shared(work, c):
    """Processor sharing: time at which the last task ends when n running tasks share c cores."""
    t, done, rem = 0.0, 0.0, sorted(work)
    for k, w in enumerate(rem):
        n = len(rem) - k
        t += (w - done) / min(1.0, c / n)
        done = w
    return t


def predict(o, hyp, c, ssh):
    colname = TYPE[o[1]] if hyp == "H1" else "cloud_vm1_std2"
    return ssh + shared([float(P[t][colname]) for t in o[2]], c)


def fit(obs, hyp, ssh):
    best = None
    for k in range(80, 301):
        c = k / 100
        mae = sum(abs(predict(o, hyp, c, ssh) - o[3]) for o in obs) / len(obs)
        if best is None or mae < best[1] - 1e-12:
            best = (c, mae)
    return best[0]


def errors(obs, hyp, c, ssh):
    e = [predict(o, hyp, c, ssh) - o[3] for o in obs]
    return sum(map(abs, e)) / len(e), 100 * sum(abs(x) / o[3] for x, o in zip(e, obs)) / len(e)


def main():
    runs = sys.argv[1:] or sorted(d for d in glob.glob(os.path.join(ROOT, "results/td[34]/*"))
                                  if os.path.exists(os.path.join(d, "allocation.csv")) and os.path.basename(d) not in SKIP
                                  and "opt" not in os.path.basename(d) and "lpt" not in os.path.basename(d))
    obs = [o for r in runs for o in observations(r)]
    ssh = 3.0
    out = [f"# Calibration du modèle de durée ({len(runs)} runs réels, {len(obs)} points VM)", "",
           f"Modèle : partage du processeur, c cœurs effectifs par VM, chaque tâche en cours avance à la vitesse min(1, c/n) ; finish = SSH + fin de la dernière tâche. SSH = {ssh} s (TD3).", "",
           "| hypothèse sur p_ij | c ajusté | erreur moyenne (MAE) | erreur relative (MAPE) | validation croisée (MAE, run laissé de côté) |",
           "|---|---:|---:|---:|---:|"]
    fitted = {}
    for hyp, name in (("H1", "H1 : chaque VM avec la colonne de son type"), ("H2", "H2 : toutes les VMs à la vitesse e2-standard-2")):
        c = fit(obs, hyp, ssh)
        mae, mape = errors(obs, hyp, c, ssh)
        loo = []
        for r in runs:
            train = [o for o in obs if o[0] != os.path.relpath(r, ROOT)]
            test = [o for o in obs if o[0] == os.path.relpath(r, ROOT)]
            ct = fit(train, hyp, ssh)
            loo += [abs(predict(o, hyp, ct, ssh) - o[3]) for o in test]
        fitted[hyp] = c
        out.append(f"| {name} | {c:.2f} | {mae:.2f} s | {mape:.1f} % | {sum(loo) / len(loo):.2f} s |")
    out += ["", "| run | VM | tâches | mesuré (s) | prédit H1 (s) | prédit H2 (s) |", "|---|---|---|---:|---:|---:|"]
    for o in obs:
        out.append(f"| {o[0]} | {o[1]} | {len(o[2])} | {o[3]:.1f} | {predict(o, 'H1', fitted['H1'], ssh):.1f} | {predict(o, 'H2', fitted['H2'], ssh):.1f} |")
    text = "\n".join(out) + "\n"
    path = os.path.join(ROOT, "results/model_fit.md")
    open(path, "w").write(text)
    print(text + f"written: {path}")


if __name__ == "__main__":
    main()
