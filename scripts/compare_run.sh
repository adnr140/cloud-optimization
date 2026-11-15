#!/usr/bin/env bash
# compare_run.sh — one fair comparison session on the real VMs: Round-Robin vs LPT vs opt.
# Usage: scripts/compare_run.sh [REPS]      (VMs RUNNING and deployed; default REPS=5)
# All in the same session, because a stop/start can move an E2 VM to another CPU platform:
#   1. measure_p.sh: platform + p_ij measured today            -> data/p_matrix_now.csv, data/vms_now.csv
#   2. bin/optimizer on today's p: allocations A (tasks.csv): rr, opt ; B (tasks_b.csv): rr, lpt, opt
#   3. every allocation run REPS times, order rotated at each repetition (no allocation always first)
#   4. summary: predicted vs measured makespan, mean / min / max, gain vs Round-Robin -> summary.md
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$ROOT"
REPS="${1:-5}"
S="results/project/session_$(date +%Y%m%d_%H%M)"; mkdir -p "$S/alloc"
echo "session -> $S"
bash scripts/measure_p.sh "$S"
OPT=(bin/optimizer -p data/p_matrix_now.csv -vms data/vms_now.csv)
gen() { "${OPT[@]}" -method "$1" -tasks "$2" -out "$S/alloc/$3.csv" | grep -E "predicted|status"
        bash scripts/check_allocation.sh "$2" data/machines.csv "$S/alloc/$3.csv" >/dev/null; }
gen rr  data/tasks.csv   A_rr
gen opt data/tasks.csv   A_opt
gen rr  data/tasks_b.csv B_rr
gen lpt data/tasks_b.csv B_lpt
gen opt data/tasks_b.csv B_opt
NAMES=(A_rr A_opt B_rr B_lpt B_opt)
for r in $(seq 1 "$REPS"); do
  for k in "${!NAMES[@]}"; do
    a=${NAMES[$(( (k + r - 1) % ${#NAMES[@]} ))]}
    echo "== repetition $r/$REPS: $a"
    PS_SNAPSHOT=0 bash scripts/run_all.sh "$S/alloc/$a.csv" "$S/rep$r/$a" | tail -1
  done
done
python3 scripts/session_summary.py "$S"
