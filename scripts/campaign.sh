#!/usr/bin/env bash
# campaign.sh — full TD1 campaign driven by config/campaign.conf (<workload> <size1> <size2> ...).
# Usage: scripts/campaign.sh [-r runs (3)] [-W warmups (1)]
# Runs are INTERLEAVED (pass 1 = every config once, then pass 2...) so machine drift spreads
# over all configs. Warm-up runs are not recorded. Old CSV is kept as .bak, never overwritten.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONF="$ROOT/config/campaign.conf" OUT="$ROOT/data/benchmark_local.csv" RUNS=3 WARMUP=1
while getopts "r:W:" o; do case "$o" in r) RUNS="$OPTARG";; W) WARMUP="$OPTARG";; *) exit 1;; esac; done
[[ -f "$CONF" ]] || { echo "campaign.sh: ERROR: missing $CONF" >&2; exit 1; }
mapfile -t CONFIGS < <(grep -vE '^\s*(#|$)' "$CONF" | awk '{for(i=2;i<=NF;i++) print $1, $i}')
for w in $(printf '%s\n' "${CONFIGS[@]}" | cut -d' ' -f1 | sort -u); do
  [[ -x "$ROOT/bin/$w" ]] || { echo "campaign.sh: ERROR: missing bin/$w" >&2; exit 1; }
done
[[ -s "$OUT" ]] && mv "$OUT" "$OUT.$(date +%Y%m%d-%H%M%S).bak"
rm -f "$ROOT"/data/raw/*.log
{ echo "campaign_start=$(date -Is) host=$(hostname)"; echo "runs=$RUNS warmups=$WARMUP order=interleaved"
  echo "loadavg_before=$(cut -d' ' -f1-3 /proc/loadavg)"; echo "md5:"; md5sum "$ROOT"/workloads/*.go
  echo "configs:"; printf '  %s\n' "${CONFIGS[@]}"; } > "$ROOT/data/campaign_meta.txt"
if (( WARMUP > 0 )); then echo "== warm-up (not recorded)"
  for c in "${CONFIGS[@]}"; do read -r w s <<<"$c"; "$ROOT/bin/$w" --size "$s" >/dev/null; done; fi
for ((run = 1; run <= RUNS; run++)); do
  echo "== pass $run/$RUNS"
  for c in "${CONFIGS[@]}"; do read -r w s <<<"$c"; bash "$ROOT/scripts/benchmark.sh" -w "$w" -s "$s" -r 1 -k "$run" -o "$OUT"; done
done
{ echo "loadavg_after=$(cut -d' ' -f1-3 /proc/loadavg)"; echo "campaign_end=$(date -Is)"; } >> "$ROOT/data/campaign_meta.txt"
echo "== done: $(($(wc -l < "$OUT") - 1)) rows in $OUT"
