#!/usr/bin/env bash
# makespan.sh — measured makespan of one run_all.sh run (controller clock, SSH included).
# Usage: scripts/makespan.sh results/<td>/<run>
# Per VM: tasks, sum of the workloads' own runtime_s, finish time of the last task (s after the first launch).
# makespan = last end_epoch - first launch_epoch over all tasks: the time the user waits for run_all.sh.
set -euo pipefail
RUN="${1:?usage: $0 RESULTS_DIR}"
for m in "$RUN"/*.meta; do
  awk -F= '{v[$1]=$2} END{print v["vm"], v["launch_epoch"], v["end_epoch"], v["remote_runtime_s"], v["task_id"]}' "$m"
done | awk '
  { vm=$1; if (!(vm in n)) ord[++k]=vm; n[vm]++; rt[vm]+=$4; if ($3>e[vm]) e[vm]=$3; if (t0==""||$2<t0) t0=$2; if ($3>T) T=$3; l[vm]=l[vm] " " $5 }
  END { printf "%-13s %5s %13s %10s  %s\n","vm","tasks","sum_runtime_s","finish_s","tasks"
        for(i=1;i<=k;i++){v=ord[i]; printf "%-13s %5d %13.1f %10.1f %s\n", v, n[v], rt[v], e[v]-t0, l[v]}
        printf "measured makespan: %.1f s\n", T-t0 }'
