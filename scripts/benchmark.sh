#!/usr/bin/env bash
# benchmark.sh — run ONE workload at ONE size N times, append one CSV row per run.
# Usage: scripts/benchmark.sh -w <workload> -s <size> [-r runs] [-o csv] [-k first_run_index] [-W warmups]
#   -w workload (bin/<workload>)  -s --size value  -r repetitions (3)  -o CSV (data/benchmark_local.csv)
#   -k first run index (1)        -W unrecorded warm-up runs (0)
# CSV: workload,size,run,runtime_s,max_rss_kb  (GNU time %e = wall clock, %M = max RSS in KB)
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GNU_TIME=/usr/bin/time
WORKLOAD="" SIZE="" RUNS=3 OUT="$ROOT/data/benchmark_local.csv" FIRST=1 WARMUP=0
HEADER="workload,size,run,runtime_s,max_rss_kb"
die() { echo "benchmark.sh: ERROR: $*" >&2; exit 1; }
while getopts "w:s:r:o:k:W:h" opt; do
  case "$opt" in
    w) WORKLOAD="$OPTARG" ;; s) SIZE="$OPTARG" ;; r) RUNS="$OPTARG" ;;
    o) OUT="$OPTARG" ;; k) FIRST="$OPTARG" ;; W) WARMUP="$OPTARG" ;;
    h) sed -n '2,6p' "$0"; exit 0 ;; *) die "unknown option (see -h)" ;;
  esac
done
# ---- checks BEFORE the experiment
[[ -n "$WORKLOAD" ]] || die "missing -w <workload>"
[[ "$SIZE"   =~ ^[1-9][0-9]*$ ]] || die "size must be a positive integer (got '$SIZE')"
[[ "$RUNS"   =~ ^[1-9][0-9]*$ ]] || die "runs must be a positive integer (got '$RUNS')"
[[ "$FIRST"  =~ ^[1-9][0-9]*$ ]] || die "first run index must be a positive integer"
[[ "$WARMUP" =~ ^[0-9]+$ ]]      || die "warm-up count must be >= 0"
BIN="$ROOT/bin/$WORKLOAD"
[[ -f "$BIN" ]] || die "executable not found: $BIN (compile it first: go build -o bin/$WORKLOAD workloads/$WORKLOAD.go)"
[[ -x "$BIN" ]] || die "file is not executable: $BIN"
[[ -x "$GNU_TIME" ]] || die "GNU time not found at $GNU_TIME (Ubuntu: sudo apt install time)"
mkdir -p "$(dirname "$OUT")" "$ROOT/data/raw"
if [[ ! -s "$OUT" ]]; then echo "$HEADER" > "$OUT"
elif [[ "$(head -n1 "$OUT")" != "$HEADER" ]]; then die "$OUT has an unexpected header; refusing to mix schemas"; fi
TMP_T="$(mktemp)"; TMP_O="$(mktemp)"; trap 'rm -f "$TMP_T" "$TMP_O"' EXIT
run_once() {
  if ! "$GNU_TIME" -f "%e %M" -o "$TMP_T" "$BIN" --size "$SIZE" >"$TMP_O" 2>&1; then
    echo "--- workload output ---" >&2; cat "$TMP_O" >&2
    die "execution failed: $WORKLOAD --size $SIZE (exit code != 0); no row written"
  fi
}
for ((w = 1; w <= WARMUP; w++)); do run_once; done
# ---- measured runs: one CSV row per execution
for ((i = 0; i < RUNS; i++)); do
  run=$((FIRST + i)); run_once
  read -r elapsed rss < <(tail -n1 "$TMP_T")
  [[ "$elapsed" =~ ^[0-9]+(\.[0-9]+)?$ && "$rss" =~ ^[0-9]+$ ]] || die "could not parse GNU time output: $(cat "$TMP_T")"
  echo "$WORKLOAD,$SIZE,$run,$elapsed,$rss" >> "$OUT"
  { echo "# $(date -Is) $WORKLOAD size=$SIZE run=$run"; cat "$TMP_O"; } >> "$ROOT/data/raw/$WORKLOAD.log"
  echo "  $WORKLOAD size=$SIZE run=$run  runtime=${elapsed}s  max_rss=${rss}KB"
done
