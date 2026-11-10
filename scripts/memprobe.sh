#!/usr/bin/env bash
# memprobe.sh — explain memory_task scaling: split wall time into user / system time and count page faults.
# Usage: scripts/memprobe.sh [tag] [sizes...]   default sizes: 256 512 1024 2048
# Hypothesis to test (TD1 open point): fixed costs + kernel page-fault work (first touch of every page)
# rather than the 5 passes over the array. Output: data/memprobe_<tag>.csv (not part of the main schema).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TAG="${1:-local}"; shift || true; SIZES=("${@:-256 512 1024 2048}"); read -ra SIZES <<<"${SIZES[*]}"
OUT="$ROOT/data/memprobe_${TAG}.csv"
THP="$(cat /sys/kernel/mm/transparent_hugepage/enabled 2>/dev/null || echo n/a)"
echo "size_mb,run,wall_s,user_s,sys_s,minor_faults,max_rss_kb,thp" > "$OUT"
for run in 1 2 3; do for s in "${SIZES[@]}"; do
  /usr/bin/time -f "%e,%U,%S,%R,%M" -o /tmp/memprobe.$$ "$ROOT/bin/memory_task" --size "$s" >/dev/null
  echo "$s,$run,$(cat /tmp/memprobe.$$),\"$THP\"" >> "$OUT"
done; done; rm -f /tmp/memprobe.$$
echo "THP setting: $THP"
awk -F, 'NR>1{k=$1; n[k]++; w[k]+=$3; u[k]+=$4; s[k]+=$5; f[k]+=$6}
  END{printf "%8s %8s %8s %8s %12s %10s\n","size_mb","wall","user","sys","faults","faults/MB"
      for(k in n) printf "%8d %8.2f %8.2f %8.2f %12d %10.1f\n",k,w[k]/n[k],u[k]/n[k],s[k]/n[k],f[k]/n[k],f[k]/n[k]/k}' "$OUT" | sort -n
echo "written: $OUT"
