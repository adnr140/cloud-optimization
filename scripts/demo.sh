#!/usr/bin/env bash
# demo.sh — live oral demo, step by step, readable from the back of the room.
#   1. the optimiser, stage by stage, on lot B with the TD2 durations (the slide 9 example):
#      Round-Robin -> LPT -> descent -> ILS -> branch and bound, one bar per VM
#   2. today's plan: the same pipeline on the durations re-measured for this session
#   3. run it on the 3 GCP VMs (run_all.sh), check it, and draw measured vs predicted
# Usage: scripts/demo.sh [SESSION_DIR]   (default results/project/session_20261113_1951)
#        NORUN=1 scripts/demo.sh         parts 1 and 2 only, no VM needed
#        AUTO=1  scripts/demo.sh         no pause between steps
set -euo pipefail
export LC_NUMERIC=C      # printf/awk read "15.9" whatever the WSL locale
cd "$(dirname "$0")/.."

S=${1:-results/project/session_20261113_1951}
TASKS=data/tasks_b.csv
OUTDIR=results/demo
OPT=bin/optimizer
[ -x "$OPT" ] || make -s optimizer

# ---------------------------------------------------------------- look
OR=$'\e[38;5;208m'; CY=$'\e[38;5;45m'; GR=$'\e[38;5;42m'; DIM=$'\e[38;5;245m'; B=$'\e[1m'; R=$'\e[0m'
SCALE=2          # characters per second
pause() { [ "${AUTO:-0}" = 1 ] && { sleep 1; return; }; printf "%s  [Enter]%s" "$DIM" "$R"; read -r _; }
title() { printf "\n%s%s━━ %s %s%s\n\n" "$B" "$CY" "$1" "$(printf '━%.0s' $(seq 1 $((60 - ${#1}))))" "$R"; }

# bars <optimizer output> <bound or empty> : one bar per VM, orange = the VM that finishes last
bars() {
  awk -v cor="$OR" -v ccy="$CY" -v cdim="$DIM" -v crs="$R" -v sc="$SCALE" -v lb="${2:-0}" '
    /^cloudopt-vm/ { n++; vm[n]=substr($1,10); f[n]=$7; t=""; for(i=8;i<=NF;i++) t=t" "$i; tk[n]=t; if($7>mx) mx=$7 }
    END {
      lc = int(lb*sc + 0.5)
      for (i=1;i<=n;i++) {
        len = int(f[i]*sc + 0.5); c = (f[i] >= mx - 0.05) ? cor : ccy
        s = ""
        for (k=1;k<=len;k++) s = s ((lb>0 && k==lc) ? "┃" : "█")
        pad = ""; vis = len; if (lb>0 && len < lc) { for (k=len+1;k<lc;k++) pad = pad " "; pad = pad cdim "┊" crs; vis = lc }
        for (k=vis;k<46;k++) pad = pad " "
        printf "  %-4s %s%s%s%s %s%5.1f s%s %s%s%s\n", vm[i], c, s, crs, pad, c, f[i], crs, cdim, tk[i], crs
      }
    }' <<<"$1"
}
summary() { sed -n 's/.*summary //p' <<<"$1" | tr ' ' '\n' | sed -n "s/^$2=//p"; }
ms() { printf "%.1f" "$(summary "$1" makespan)"; }

# ---------------------------------------------------------------- 1. the algorithm, stage by stage
title "1. The algorithm step by step · batch B, TD2 runtimes"
printf "  10 tasks, 3 VMs: %s3^10 = 59,049 possible plans%s. Orange = the VM that finishes last.\n\n" "$B" "$R"
rr=$($OPT -method rr -tasks $TASKS)
lb=$(summary "$rr" lower_bound)
printf "  %sLower bound%s ┊ %.1f s: no plan can finish earlier.\n\n" "$B" "$R" "$lb"
pause

show() {   # show <method> <label> <explanation>
  local o; o=$($OPT -method "$1" -tasks $TASKS)
  printf "  %s%-36s%s %s%s s%s\n" "$B" "$2" "$R" "$OR$B" "$(ms "$o")" "$R"
  printf "  %s%s%s\n" "$DIM" "$3" "$R"
  bars "$o" "$lb"; echo
  LAST=$o
}
show rr  "Start · Round-Robin"             "task i goes to VM i mod 3, ignoring runtimes"
pause
show lpt "1. Build · LPT (CM3)"            "Longest Processing Time: longest task first, on the VM that finishes earliest"
pause
show ls  "2. Improve · local search (CM5)" "from the slowest VM: move 1 task, swap 2, or 2 for 1"
pause
show ils "3. Iterate · ILS (CM5)"          "Iterated Local Search: 200 kicks of the plan, each followed by a local search"
pause
o=$($OPT -method opt -tasks $TASKS)
bb=$(grep '^bound' <<<"$o" | sed -E 's/.*plans; ([0-9]+) nodes, ([0-9]+) complete plans, ([0-9]+) branches pruned.*/\1 nodes explored, \2 complete plans computed, \3 branches pruned/')
printf "  %s%-36s%s %s%s s · OPTIMAL%s\n" "$B" "4. Prove · Branch & Bound (CM4)" "$R" "$OR$B" "$(ms "$o")" "$R"
printf "  %sexplores the tree of plans, prunes every branch that cannot beat the record%s\n" "$DIM" "$R"
printf "  %s→ %s%s\n" "$GR" "$bb" "$R"
printf "  %s→ 59,049 plans covered in %s ms: proven, no plan can do better in the model%s\n\n" \
  "$GR$B" "$(printf '%.0f' "$(summary "$o" time_ms)")" "$R"
pause

# ---------------------------------------------------------------- 2. today's plan
title "2. Today's plan · re-measured runtimes ($S)"
o=$($OPT -method opt -tasks $TASKS -p "$S/p_matrix_now.csv" -vms "$S/vms_now.csv" -out data/allocation_demo.csv)
grep -E '^(construct|improve|iterate|bound|status)' <<<"$o" | sed "s/^/  $DIM/; s/\$/$R/"
echo
lb2=$(summary "$o" lower_bound)
bars "$o" "$lb2"
PRED=$(ms "$o")
printf "\n  %sOPTIMAL · %s s predicted%s · bound %.1f s · %s ms → %sdata/allocation_demo.csv%s\n\n" \
  "$OR$B" "$PRED" "$R" "$lb2" "$(printf '%.0f' "$(summary "$o" time_ms)")" "$B" "$R"
[ "${NORUN:-0}" = 1 ] && exit 0
pause

# ---------------------------------------------------------------- 3. run it on the VMs
title "3. Parallel run on the 3 GCP VMs"
rm -rf "$OUTDIR"
scripts/run_all.sh data/allocation_demo.csv "$OUTDIR" 2>&1 | while IFS= read -r l; do
  case "$l" in
    *" launch "*) printf "  %s%s%s\n" "$DIM" "$l" "$R" ;;
    *" done "*)   printf "  %s%s%s\n" "$GR" "$l" "$R" ;;
    *"CHECK OK"*) printf "\n  %s%s%s\n" "$GR$B" "$l" "$R" ;;
    *"CHECK FAILED"*|*FAIL*) printf "  %s%s%s\n" "$OR$B" "$l" "$R" ;;
    *"cloudopt-vm"*": "*) printf "  %s\n" "$l" ;;
    *"max workload"*) printf "\n  %s\n" "$l" ;;
  esac
done
echo
m=$(scripts/makespan.sh "$OUTDIR")
# makespan.sh: vm tasks sum finish tasks -> reorder as optimizer columns for bars()
meas=$(awk '/^cloudopt-vm/ {printf "%s x x x x x %s", $1, $4; for(i=5;i<=NF;i++) printf " %s", $i; print ""}' <<<"$m" | sort)
printf "  %sMeasured%s (real finish of each VM, VM clocks)\n" "$B" "$R"
bars "$meas" "$lb2"
MEAS=$(sed -n 's/^measured makespan: \([0-9.]*\).*/\1/p' <<<"$m")
printf "\n  %sPredicted %s s · measured %s s%s\n\n" "$B" "$PRED" "$MEAS" "$R"
printf "  %sAfter the talk: scripts/gcp.sh stop-all%s\n" "$DIM" "$R"
