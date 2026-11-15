#!/usr/bin/env bash
# check_allocation.sh — TD4 Part 4: is a GENERATED allocation valid? (no VM, no gcloud needed)
# Usage: scripts/check_allocation.sh TASKS_CSV MACHINES_CSV ALLOCATION_CSV
# Checks the TD4 rules: header exactly task_id,workload,size,vm ; every task of TASKS_CSV appears exactly once ;
# no extra task ; workload and size unchanged ; every VM belongs to MACHINES_CSV. Prints the task count per VM.
# Works for ANY scheduler (Round-Robin now, the optimised one in TD5). Exit 0 = valid, 1 = invalid.
set -uo pipefail
T="${1:?usage: $0 TASKS MACHINES ALLOCATION}"; M="${2:?}"; A="${3:?}"
for f in "$T" "$M" "$A"; do [[ -f "$f" ]] || { echo "check_allocation: missing $f" >&2; exit 2; }; done
awk -F, -v T="$T" -v M="$M" -v A="$A" '
  { gsub(/\r/,"") }
  FILENAME==T && FNR==1 { next }
  FILENAME==T && NF     { want[$1]=$2","$3; order[++nt]=$1; next }
  FILENAME==M && FNR==1 { next }
  FILENAME==M && NF     { vm[$1]=1; vms[++nm]=$1; count[$1]=0; next }
  FILENAME==A && FNR==1 { if ($0!="task_id,workload,size,vm") { print "  header is \"" $0 "\", expected task_id,workload,size,vm"; err++ } next }
  FILENAME==A && NF {
    if (++seen[$1]>1)               { print "  task " $1 " appears more than once"; err++ }
    if (!($1 in want))              { print "  task " $1 " is not in " T; err++; next }
    if (want[$1]!=$2","$3)          { print "  task " $1 ": workload,size " $2","$3 " changed (expected " want[$1] ")"; err++ }
    if (!($4 in vm))                { print "  task " $1 ": VM \"" $4 "\" is not in " M; err++ }
    else count[$4]++
  }
  END {
    for (i=1;i<=nt;i++) if (!(order[i] in seen)) { print "  task " order[i] " is missing"; err++ }
    line=""; for (i=1;i<=nm;i++) line=line " " vms[i] "=" count[vms[i]]
    print "  tasks per VM:" line
    if (err) { print "ALLOCATION INVALID: " err " problem(s) in " A; exit 1 }
    print "ALLOCATION OK: " nt " tasks, each exactly once, unchanged, on known VMs (" A ")"
  }' "$T" "$M" "$A"
