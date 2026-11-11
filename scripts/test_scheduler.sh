#!/usr/bin/env bash
# test_scheduler.sh — TD4 Part 4.1: test a scheduler binary on small inputs, without any VM.
# Usage: scripts/test_scheduler.sh [SCHEDULER_BIN]   (default bin/round_robin_scheduler)
# Cases A-E of the TD + determinism + "not hard-coded" (other task/VM counts). Exit 1 if any case fails.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${1:-$ROOT/bin/round_robin_scheduler}"
[[ -x "$BIN" ]] || { echo "missing $BIN (run: make scheduler)" >&2; exit 2; }
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
pass=0; fail=0
ok()  { echo "PASS  $1"; pass=$((pass+1)); }
ko()  { echo "FAIL  $1"; fail=$((fail+1)); }
tasks() { echo task_id,workload,size; for i in $(seq 1 "$1"); do echo "T$i,cpu_task,$((i*1000))"; done; }
machines() { echo vm; for i in $(seq 1 "$1"); do echo "vm$i"; done; }
counts() { tail -n +2 "$1" | cut -d, -f4 | sort | uniq -c | awk '{printf "%s=%s ", $2, $1}' | sed 's/ $//'; }

# expect_ok NAME NTASKS NVMS EXPECTED_COUNTS
expect_ok() {
  tasks "$2" >"$TMP/t.csv"; machines "$3" >"$TMP/m.csv"
  if "$BIN" "$TMP/t.csv" "$TMP/m.csv" "$TMP/a.csv" >/dev/null 2>"$TMP/err" \
     && "$ROOT/scripts/check_allocation.sh" "$TMP/t.csv" "$TMP/m.csv" "$TMP/a.csv" >/dev/null \
     && [[ "$(counts "$TMP/a.csv")" == "$4" ]]; then ok "$1: $(counts "$TMP/a.csv")"
  else ko "$1: got '$(counts "$TMP/a.csv" 2>/dev/null)' expected '$4' $(cat "$TMP/err")"; fi
}
# expect_error NAME   (inputs already in $TMP/t.csv and $TMP/m.csv)
expect_error() {
  rm -f "$TMP/a.csv"
  if "$BIN" "$TMP/t.csv" "$TMP/m.csv" "$TMP/a.csv" >/dev/null 2>"$TMP/err"; then ko "$1: exit 0, an allocation was produced"
  elif [[ -e "$TMP/a.csv" ]]; then ko "$1: error reported but an allocation file was still written"
  else ok "$1: error -> $(cat "$TMP/err")"; fi
}

expect_ok "A  6 tasks, 3 VMs" 6 3 "vm1=2 vm2=2 vm3=2"
expect_ok "B  5 tasks, 2 VMs" 5 2 "vm1=3 vm2=2"
tasks 5 >"$TMP/t.csv"; machines 2 >"$TMP/m.csv"; "$BIN" "$TMP/t.csv" "$TMP/m.csv" "$TMP/a.csv" >/dev/null
[[ "$(tail -n +2 "$TMP/a.csv" | cut -d, -f4 | tr '\n' ' ')" == "vm1 vm2 vm1 vm2 vm1 " ]] && ok "B' assignments alternate vm1 vm2 vm1 vm2 vm1" || ko "B' not alternating"
expect_ok "C  2 tasks, 3 VMs (vm3 gets none)" 2 3 "vm1=1 vm2=1"
tasks 5 >"$TMP/t.csv"; machines 0 >"$TMP/m.csv"; expect_error "D  5 tasks, 0 VMs"
printf 'task_id,workload,size\nT1,cpu_task,1000\nT1,cpu_task,2000\n' >"$TMP/t.csv"; machines 3 >"$TMP/m.csv"; expect_error "E  duplicate task ID"
# extra invalid inputs (TD: "report errors for invalid input instead of silently creating a broken allocation")
printf 'id,workload,size\nT1,cpu_task,1000\n' >"$TMP/t.csv"; expect_error "E2 wrong header in tasks.csv"
printf 'task_id,workload,size\nT1,cpu_task\n' >"$TMP/t.csv"; expect_error "E3 row with a missing field"
tasks 3 >"$TMP/t.csv"; printf 'vm\nvm1\nvm1\n' >"$TMP/m.csv"; expect_error "E4 duplicated VM in machines.csv"
# not hard-coded: other sizes
expect_ok "F  10 tasks, 3 VMs" 10 3 "vm1=4 vm2=3 vm3=3"
expect_ok "G  9 tasks, 1 VM" 9 1 "vm1=9"
expect_ok "H  100 tasks, 7 VMs" 100 7 "vm1=15 vm2=15 vm3=14 vm4=14 vm5=14 vm6=14 vm7=14"
# determinism: same ordered inputs -> byte-identical output
tasks 10 >"$TMP/t.csv"; machines 3 >"$TMP/m.csv"
"$BIN" "$TMP/t.csv" "$TMP/m.csv" "$TMP/a1.csv" >/dev/null; "$BIN" "$TMP/t.csv" "$TMP/m.csv" "$TMP/a2.csv" >/dev/null
cmp -s "$TMP/a1.csv" "$TMP/a2.csv" && ok "I  deterministic (two runs, identical files)" || ko "I  two runs differ"
# order sensitivity: reversing tasks.csv moves tasks to other VMs
{ echo task_id,workload,size; tail -n +2 "$TMP/t.csv" | tac; } >"$TMP/r.csv"
"$BIN" "$TMP/r.csv" "$TMP/m.csv" "$TMP/ar.csv" >/dev/null
moved=$(join -t, <(tail -n +2 "$TMP/a1.csv" | cut -d, -f1,4 | sort) <(tail -n +2 "$TMP/ar.csv" | cut -d, -f1,4 | sort) | awk -F, '$2!=$3' | wc -l)
(( moved > 0 )) && ok "J  reversed task order: $moved/10 tasks change VM (RR depends on the order)" || ko "J  order had no effect"

echo "---- $pass passed, $fail failed"
(( fail == 0 ))
