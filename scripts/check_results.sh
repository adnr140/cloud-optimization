#!/usr/bin/env bash
# check_results.sh — TD3 Part 10: validate one distributed run.
# Usage: scripts/check_results.sh results/td3/<run>
# For every task of <run>/allocation.csv: launched exactly once (launch.log), .out/.err/.meta present,
# executed on the VM of the allocation (remote hostname), exit code 0, JSON output with the right task/size.
# Also reports how many tasks overlapped on each VM (controller-side launch/end times, NOT a benchmark).
# Exit 0 only if every task is OK. Writes <run>/check.txt.
set -uo pipefail
RUN="${1:?usage: $0 RESULTS_DIR}"
[[ -f "$RUN/allocation.csv" ]] || { echo "no $RUN/allocation.csv" >&2; exit 2; }
get() { sed -n "s/^$2=//p" "$1" 2>/dev/null; }
fail=0; n=0
{
printf '%-5s %-12s %-10s %-14s %-14s %4s %8s %8s  %s\n' task workload size vm remote_host rc start_s end_s status
t0=$(cut -d, -f1 "$RUN/launch.log" | sort -n | head -1)
while IFS=, read -r id w s vm; do
  n=$((n+1)); m="$RUN/$id.meta"; problems=()
  launches=$(grep -c ",$id,$vm\$" "$RUN/launch.log" 2>/dev/null || true)
  [[ "$launches" == 1 ]] || problems+=("launched ${launches:-0} times")
  for f in out err meta; do [[ -f "$RUN/$id.$f" ]] || problems+=("missing $id.$f"); done
  rc=$(get "$m" exit_code); host=$(get "$m" remote_host)
  [[ "$rc" == 0 ]] || problems+=("exit ${rc:-?}, see $id.err")
  [[ "$host" == "$vm" ]] || problems+=("ran on '${host}' instead of $vm")
  grep -Eq "\"task\":\"$w\",\"size(_mb)?\":$s[,}]" "$RUN/$id.out" 2>/dev/null \
    || problems+=("no $w size $s JSON line in $id.out")
  st=$(get "$m" launch_epoch); en=$(get "$m" end_epoch)
  rs=$(awk -v a="${st:-0}" -v b="$t0" 'BEGIN{printf "%.1f", a-b}'); re=$(awk -v a="${en:-0}" -v b="$t0" 'BEGIN{printf "%.1f", a-b}')
  if [[ ${#problems[@]} -eq 0 ]]; then status=OK; else status="FAIL: $(IFS=';'; echo "${problems[*]}")"; fail=$((fail+1)); fi
  printf '%-5s %-12s %-10s %-14s %-14s %4s %8s %8s  %s\n' "$id" "$w" "$s" "$vm" "${host:--}" "${rc:--}" "$rs" "$re" "$status"
done < <(tail -n +2 "$RUN/allocation.csv" | tr -d '\r' | grep -v '^[[:space:]]*$')
extra=$(ls "$RUN" | sed -n 's/\.out$//p' | grep -vxF -f <(tail -n +2 "$RUN/allocation.csv" | cut -d, -f1) || true)
[[ -z "$extra" ]] || { echo "unexpected outputs (task not in allocation): $extra"; fail=$((fail+1)); }
echo
echo "max workload processes running at the same time, per VM (VM clock: start on the VM + runtime_s):"
for f in "$RUN"/*.meta; do
  vm=$(get "$f" vm); a=$(get "$f" remote_start_epoch); d=$(get "$f" remote_runtime_s)
  [[ -n "$a" && -n "$d" ]] || continue
  echo "$vm $a 1"; awk -v a="$a" -v d="$d" -v v="$vm" 'BEGIN{printf "%s %.6f -1\n", v, a+d}'
done | sort -k1,1 -k2,2n -k3,3n | awk '{c[$1]+=$3; if(c[$1]>mx[$1]) mx[$1]=c[$1]} END{for(v in mx) printf "  %s: %d\n", v, mx[v]}' | sort
echo
if [[ $fail -eq 0 ]]; then echo "CHECK OK: $n/$n tasks launched once, on the right VM, exit 0, output collected"
else echo "CHECK FAILED: $fail problem(s) out of $n tasks"; fi
} | tee "$RUN/check.txt"
[[ $(tail -n1 "$RUN/check.txt") == "CHECK OK"* ]]
