#!/usr/bin/env bash
# test_optimizer.sh — tests of bin/optimizer without any VM. Exit 1 if any test fails.
# 1 valid allocations (same checker as Round-Robin)    2 each stage never worsens: opt <= ils <= ls <= greedy, opt <= rr
# 3 opt = independent brute force; lower bound <= true optimum (scripts/bruteforce_check.py, no shared code)
# 4 RAM constraint respected     5 impossible instance -> error, no file      6 deterministic
# 7 prediction of the real runs  8 scale: 1000 tasks x 200 VMs, valid plan, status and gap reported, time limit kept
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$ROOT"
BIN=bin/optimizer; [[ -x $BIN ]] || { echo "missing $BIN (make optimizer)" >&2; exit 2; }
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
pass=0; fail=0; ok() { echo "PASS  $1"; pass=$((pass+1)); }; ko() { echo "FAIL  $1"; fail=$((fail+1)); }
sm() { "$BIN" "$@" 2>/dev/null | sed -n 's/^summary .* makespan=\([0-9.]*\) .*/\1/p'; }      # 4 decimals
lb() { "$BIN" "$@" 2>/dev/null | sed -n 's/^summary .* lower_bound=\([0-9.]*\) .*/\1/p'; }
le() { awk -v a="$1" -v b="$2" 'BEGIN{exit !(a <= b + 1e-6)}'; }
r1() { awk -v a="$1" 'BEGIN{printf "%.1f", a}'; }

for t in data/tasks.csv data/tasks_b.csv data/tasks_reordered.csv; do
  for m in opt ils lpt minmin maxmin; do
    "$BIN" -method $m -tasks $t -out "$TMP/a.csv" >/dev/null && scripts/check_allocation.sh $t data/machines.csv "$TMP/a.csv" >/dev/null \
      && ok "1 $m on $(basename $t): valid allocation" || ko "1 $m on $(basename $t): invalid allocation"
  done
  o=$(sm -method opt -tasks $t); i=$(sm -method ils -tasks $t); l=$(sm -method ls -tasks $t); g=$(sm -method greedy -tasks $t); r=$(sm -method rr -tasks $t)
  le "$o" "$i" && le "$i" "$l" && le "$l" "$g" && le "$o" "$r" && ok "2 $(basename $t): opt $o <= ils $i <= ls $l <= greedy $g; rr $r" \
    || ko "2 $(basename $t): opt $o ils $i ls $l greedy $g rr $r"
done
# random instances built only from measured (workload,size) pairs
mapfile -t KEYS < <(tail -n +2 data/p_matrix.csv | cut -d, -f1 | tr : ,)
for s in 1 2 3 4 5; do
  RANDOM=$s; { echo task_id,workload,size; for i in $(seq 1 8); do echo "R$i,${KEYS[$((RANDOM % ${#KEYS[@]}))]}"; done; } > "$TMP/r$s.csv"
  o=$(sm -method opt -tasks "$TMP/r$s.csv"); b=$(python3 scripts/bruteforce_check.py "$TMP/r$s.csv"); L=$(lb -method opt -tasks "$TMP/r$s.csv")
  [[ "$(r1 $o)" == "$b" ]] && ok "3 random #$s (8 tasks, 6561 plans): opt $(r1 $o) = brute force $b" || ko "3 random #$s: opt $o != brute force $b"
  le "$L" "$o" && ok "3 random #$s: lower bound $(r1 $L) <= optimum $(r1 $o)" || ko "3 random #$s: lower bound $L > optimum $o"
  i=$(sm -method ils -tasks "$TMP/r$s.csv"); g=$(sm -method greedy -tasks "$TMP/r$s.csv")
  le "$o" "$i" && le "$i" "$g" && ok "2 random #$s: opt $(r1 $o) <= ils $(r1 $i) <= greedy $(r1 $g)" || ko "2 random #$s: opt $o ils $i greedy $g"
done
for t in data/tasks.csv data/tasks_b.csv data/tasks_ram_trap.csv; do
  o=$(sm -method opt -tasks $t); b=$(python3 scripts/bruteforce_check.py $t)
  [[ "$(r1 $o)" == "$b" ]] && ok "3 $(basename $t): opt $(r1 $o) = brute force $b" || ko "3 $(basename $t): opt $o != brute force $b"
done
# RAM: Round-Robin puts both 2 GB memory tasks on one 4 GB VM; the optimiser must not
if "$BIN" -method rr -tasks data/tasks_ram_trap.csv >/dev/null 2>"$TMP/err"; then ko "4 rr on ram trap should be infeasible"; else ok "4 rr on ram trap: $(cut -c1-60 "$TMP/err")..."; fi
for m in opt lpt minmin maxmin; do
  "$BIN" -method $m -tasks data/tasks_ram_trap.csv -out "$TMP/ram.csv" >/dev/null
  bad=$(awk -F, 'NR>1 && $2=="memory_task" && $3=="2048"{n[$4]++} END{for(v in n) if(n[v]>1 && v!="cloudopt-vm1") print v}' "$TMP/ram.csv")
  [[ -z $bad ]] && ok "4 $m on ram trap: no 4 GB VM gets both 2 GB tasks" || ko "4 $m on ram trap: $bad overloaded"
done
# impossible: 6 x 2 GB tasks cannot fit (7.5 + 3.5 + 3.5 GB usable)
{ echo task_id,workload,size; for i in 1 2 3 4 5 6; do echo "M$i,memory_task,2048"; done; } > "$TMP/imp.csv"
rm -f "$TMP/imp_out.csv"
if "$BIN" -method opt -tasks "$TMP/imp.csv" -out "$TMP/imp_out.csv" >/dev/null 2>"$TMP/err"; then ko "5 impossible instance accepted"
elif [[ -e "$TMP/imp_out.csv" ]]; then ko "5 error but a file was written"; else ok "5 impossible instance: $(cat "$TMP/err")"; fi
"$BIN" -out "$TMP/d1.csv" -tasks data/tasks_b.csv >/dev/null; "$BIN" -out "$TMP/d2.csv" -tasks data/tasks_b.csv >/dev/null
cmp -s "$TMP/d1.csv" "$TMP/d2.csv" && ok "6 deterministic (opt, scenario B, two runs)" || ko "6 two runs differ"
# a node budget too small to finish the proof must give FEASIBLE, not a false OPTIMAL
"$BIN" -tasks data/tasks_b.csv -max-nodes 50 | grep -q "status FEASIBLE" && ok "6 interrupted search reports FEASIBLE (no false proof)" || ko "6 interrupted search not reported"
# the model must predict the measured runs it was calibrated on within 1.5 s (see results/model_fit.md)
for pair in allocation_rr:td4 allocation_rr_reordered:td4 allocation_manual_packed:td3; do
  a=${pair%%:*}; d=${pair##*:}; [[ -d results/$d/$a ]] || continue
  p=$(r1 "$(sm -method eval -tasks data/tasks.csv -alloc data/$a.csv)")
  r=$(scripts/makespan.sh results/$d/$a | sed -n 's/measured makespan: \([0-9.]*\) s/\1/p')
  awk -v p="$p" -v r="$r" 'BEGIN{d=p-r; if(d<0)d=-d; exit !(d<=1.5)}' && ok "7 $a: predicted $p s, measured $r s" || ko "7 $a: predicted $p s, measured $r s"
done
# scale: 1000 tasks on 200 VMs (1 e2-standard-2 for 2 e2-medium), time limit 10 s
{ echo vm,machine_type,ram_mb,p_column,eff_cores; for j in $(seq 1 200); do
    if (( j % 3 == 1 )); then echo "vm$j,e2-standard-2,8192,cloud_vm1_std2,1.25"; else echo "vm$j,e2-medium,4096,cloud_vm1,1.25"; fi; done; } > "$TMP/vms.csv"
{ echo vm; tail -n +2 "$TMP/vms.csv" | cut -d, -f1; } > "$TMP/machines.csv"
RANDOM=42; { echo task_id,workload,size; for i in $(seq 1 1000); do echo "X$i,${KEYS[$((RANDOM % ${#KEYS[@]}))]}"; done; } > "$TMP/big.csv"
t0=$(date +%s.%N); "$BIN" -tasks "$TMP/big.csv" -vms "$TMP/vms.csv" -out "$TMP/big_alloc.csv" > "$TMP/big.out"; t1=$(date +%s.%N)
el=$(awk -v a="$t0" -v b="$t1" 'BEGIN{printf "%.1f", b-a}')
st=$(sed -n 's/^summary .* gap_pct=\([0-9.-]*\) status=\([A-Z]*\) .*/\2, gap \1 %/p' "$TMP/big.out")
scripts/check_allocation.sh "$TMP/big.csv" "$TMP/machines.csv" "$TMP/big_alloc.csv" >/dev/null && [[ -n $st ]] \
  && awk -v e="$el" 'BEGIN{exit !(e <= 12)}' && ok "8 1000 tasks x 200 VMs: valid plan in $el s ($st)" || ko "8 1000 tasks: $el s, '$st'"
echo "---- $pass passed, $fail failed"; (( fail == 0 ))
