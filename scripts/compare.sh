#!/usr/bin/env bash
# compare.sh — compare two machines on the SAME (workload,size) configurations.
# Usage: scripts/compare.sh <tagA> <tagB>      e.g. scripts/compare.sh local cloud_vm1
# Reads data/workload_profile_<tag>.csv (from analyze.sh) and data/machine_<tag>.txt
# Writes results/compare_<tagA>_vs_<tagB>.md
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
A="${1:?usage: compare.sh <tagA> <tagB>}" B="${2:?usage: compare.sh <tagA> <tagB>}"
PA="$ROOT/data/workload_profile_$A.csv" PB="$ROOT/data/workload_profile_$B.csv"
for f in "$PA" "$PB"; do [[ -s "$f" ]] || { echo "compare.sh: ERROR: $f missing (run make analyze TAG=...)" >&2; exit 1; }; done
OUT="$ROOT/results/compare_${A}_vs_${B}.md"
field() { awk -F': *' -v k="$2" '$1==k{print $2; exit}' "$ROOT/data/machine_$1.txt" 2>/dev/null || true; }
{
  echo "# $A vs $B — same workloads, same sizes, same runner"
  echo
  echo "| | $A | $B |"; echo "|---|---|---|"
  for k in cpu_model logical_cpus threads/core ram_total virtualized gce_machine gce_zone gce_cpu_platform go_version; do
    echo "| $k | $(field "$A" "$k") | $(field "$B" "$k") |"
  done
  echo
  echo "| workload | size | mean $A (s) | CV $A % | mean $B (s) | CV $B % | ratio $B/$A | RSS $A (MB) | RSS $B (MB) |"
  echo "|---|---:|---:|---:|---:|---:|---:|---:|---:|"
  # profile columns: 1 workload,2 size,3 n,4 mean,5 std,6 cv,7 min,8 max,9 mean_rss_kb,10 max_rss_kb
  awk -F, 'FNR==1{next} NR==FNR{a[$1","$2]=$0; next}
    ($1","$2) in a { split(a[$1","$2],x,",")
      r=(x[4]>0)?sprintf("%.2f",$4/x[4]):"n/a"
      printf "| %s | %s | %.3f | %.1f | %.3f | %.1f | **%s** | %.1f | %.1f |\n",$1,$2,x[4],x[6],$4,$6,r,x[9]/1024,$9/1024 }' "$PA" "$PB"
  echo
  echo "ratio > 1: $B is slower than $A on this configuration. Only configurations present on both machines are listed."
} > "$OUT"
cat "$OUT"; echo; echo "written: $OUT"
