#!/usr/bin/env bash
# run_all.sh — TD3: launch every task of an allocation file on its VM, all at once, then wait.
# Usage: scripts/run_all.sh [ALLOCATION_CSV] [OUTDIR]
#   default ALLOCATION_CSV = data/allocation_manual.csv
#   default OUTDIR         = results/td3/<name of the allocation file>
# The allocation (which task on which VM) lives ONLY in the CSV; this script never changes with it.
# Steps: 1. validate the CSV (fail before launching anything)  2. launch one run_task.sh per row with &
#        3. ONE wait after the loop  4. check_results.sh (exit 1 if any task failed or is missing)
# PS_SNAPSHOT=0 disables the ps snapshot taken on every VM while the tasks run.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=../config/gcp.env
source "$ROOT/config/gcp.env"
die() { echo "run_all.sh: ERROR: $*" >&2; exit 2; }

ALLOC="${1:-$ROOT/data/allocation_manual.csv}"
[[ -f "$ALLOC" ]] || die "allocation file not found: $ALLOC"
OUTDIR="${2:-$ROOT/results/td3/$(basename "$ALLOC" .csv)}"

# ---------- 1. validation (TD3 Part 3: unique ids, known workload, VM exists and RUNNING, no empty field)
[[ "$(head -n1 "$ALLOC" | tr -d '\r')" == "task_id,workload,size,vm" ]] || die "header must be: task_id,workload,size,vm"
mapfile -t ROWS < <(tail -n +2 "$ALLOC" | tr -d '\r' | grep -v '^[[:space:]]*$')
[[ ${#ROWS[@]} -gt 0 ]] || die "no task in $ALLOC"
known_workloads=" $(cd "$ROOT/workloads" && ls *.go | sed 's/\.go$//' | tr '\n' ' ')"
running=" $(gcloud compute instances list --project "$PROJECT_ID" --filter="zone:($ZONE) AND status=RUNNING" \
            --format='value(name)' | tr '\n' ' ')"
errors=0; declare -A seen
bad() { echo "  invalid row '$row': $*" >&2; errors=$((errors+1)); }
for row in "${ROWS[@]}"; do
  IFS=, read -r id w s vm extra <<<"$row"
  if [[ -z "$id" || -z "$w" || -z "$s" || -z "$vm" || -n "${extra:-}" ]]; then bad "need exactly 4 non-empty fields"; continue; fi
  [[ -z "${seen[$id]:-}" ]] || bad "duplicate task_id $id"; seen[$id]=1
  [[ "$known_workloads" == *" $w "* ]] || bad "unknown workload $w (known:$known_workloads)"
  [[ "$s" =~ ^[0-9]+$ ]] || bad "size is not an integer"
  [[ "$running" == *" $vm "* ]] || bad "VM $vm does not exist or is not RUNNING in $ZONE"
done
[[ $errors -eq 0 ]] || die "$errors invalid row(s) in $ALLOC: nothing launched"
echo "allocation OK: ${#ROWS[@]} tasks, file $ALLOC"

# ---------- 2. launch: one background process per task, no waiting inside the loop
rm -rf "$OUTDIR"; mkdir -p "$OUTDIR"
cp "$ALLOC" "$OUTDIR/allocation.csv"
echo "results -> $OUTDIR"
for row in "${ROWS[@]}"; do
  IFS=, read -r id w s vm <<<"$row"
  echo "$(date +%s.%N),$id,$vm" >>"$OUTDIR/launch.log"         # one line per launch: proves "exactly once"
  echo "[$(date +%T)] launch $id ($w --size $s) on $vm"
  "$ROOT/scripts/run_task.sh" "$id" "$w" "$s" "$vm" "$ZONE" "$OUTDIR" </dev/null &
done
# Evidence of concurrency: while the tasks run, list the workload processes on every VM (also in background).
if [[ "${PS_SNAPSHOT:-1}" == 1 ]]; then
  ( sleep "${PS_DELAY:-1}"; "$ROOT/scripts/ps_all.sh" >"$OUTDIR/ps_snapshot.txt" 2>&1 ) </dev/null &
fi

# ---------- 3. a single wait, after ALL tasks have been launched
wait
echo "[$(date +%T)] All tasks completed"

# ---------- 4. failures are never silent: check every task, non-zero exit if anything is wrong
"$ROOT/scripts/check_results.sh" "$OUTDIR"
