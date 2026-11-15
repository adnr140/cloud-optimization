#!/usr/bin/env bash
# campaign.sh — full benchmark campaign driven by config/campaign.conf (<workload> <size1> <size2> ...).
# Usage: scripts/campaign.sh [-r runs (3)] [-W warmups (1)] [-t tag (local)]
#   tag names the machine: data/benchmark_<tag>.csv, data/campaign_meta_<tag>.txt, data/raw/<tag>/
#   (TD1: local, TD2: cloud_vm1). Same script, same sizes, same CSV schema on every machine.
# Runs are INTERLEAVED (pass 1 = every config once, then pass 2...) so machine drift spreads
# over all configs. Warm-up runs are not recorded. Old CSV is kept as .bak, never overwritten.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONF="$ROOT/config/campaign.conf" RUNS=3 WARMUP=1 TAG=local
while getopts "r:W:t:" o; do case "$o" in r) RUNS="$OPTARG";; W) WARMUP="$OPTARG";; t) TAG="$OPTARG";; *) exit 1;; esac; done
[[ "$TAG" =~ ^[a-z0-9_]+$ ]] || { echo "campaign.sh: ERROR: tag must match [a-z0-9_]+" >&2; exit 1; }
OUT="$ROOT/data/benchmark_${TAG}.csv" META="$ROOT/data/campaign_meta_${TAG}.txt" RAW="$ROOT/data/raw/$TAG"
[[ -f "$CONF" ]] || { echo "campaign.sh: ERROR: missing $CONF" >&2; exit 1; }
mapfile -t CONFIGS < <(grep -vE '^\s*(#|$)' "$CONF" | awk '{for(i=2;i<=NF;i++) print $1, $i}')
for w in $(printf '%s\n' "${CONFIGS[@]}" | cut -d' ' -f1 | sort -u); do
  [[ -x "$ROOT/bin/$w" ]] || { echo "campaign.sh: ERROR: missing bin/$w" >&2; exit 1; }
done
[[ -s "$OUT" ]] && mv "$OUT" "$OUT.$(date +%Y%m%d-%H%M%S).bak"
mkdir -p "$RAW"; rm -f "$RAW"/*.log
{ echo "campaign_start=$(date -Is) host=$(hostname) tag=$TAG"; echo "runs=$RUNS warmups=$WARMUP order=interleaved"
  echo "commit=$(git -C "$ROOT" rev-parse --short HEAD 2>/dev/null || cat "$ROOT/DEPLOYED_COMMIT" 2>/dev/null || echo unknown)"; echo "go=$(go version 2>/dev/null)"
  echo "loadavg_before=$(cut -d' ' -f1-3 /proc/loadavg)"; echo "md5:"; md5sum "$ROOT"/workloads/*.go
  echo "configs:"; printf '  %s\n' "${CONFIGS[@]}"; } > "$META"
if (( WARMUP > 0 )); then echo "== warm-up (not recorded)"
  for c in "${CONFIGS[@]}"; do read -r w s <<<"$c"; "$ROOT/bin/$w" --size "$s" >/dev/null; done; fi
for ((run = 1; run <= RUNS; run++)); do
  echo "== pass $run/$RUNS"
  for c in "${CONFIGS[@]}"; do read -r w s <<<"$c"; bash "$ROOT/scripts/benchmark.sh" -w "$w" -s "$s" -r 1 -k "$run" -o "$OUT" -L "$RAW"; done
done
{ echo "loadavg_after=$(cut -d' ' -f1-3 /proc/loadavg)"; echo "campaign_end=$(date -Is)"; } >> "$META"
echo "== done: $(($(wc -l < "$OUT") - 1)) rows in $OUT"
