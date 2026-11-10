#!/usr/bin/env bash
# calibrate.sh — one quick run per configured size, to check that runtimes are measurable
# (>= ~1 s) and manageable (< ~30 s) BEFORE launching the real campaign. Nothing is recorded.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONF="${1:-$ROOT/config/campaign.conf}"
grep -vE '^\s*(#|$)' "$CONF" | awk '{for(i=2;i<=NF;i++) print $1, $i}' | while read -r w s; do
  out=$( { /usr/bin/time -f "%e %M" "$ROOT/bin/$w" --size "$s" >/dev/null; } 2>&1 | tail -n1 )
  read -r e m <<<"$out"
  flag=""; awk -v e="$e" 'BEGIN{exit !(e<1.0)}' && flag="  <-- too short, increase size"
  awk -v e="$e" 'BEGIN{exit !(e>30.0)}' && flag="  <-- too long, decrease size"
  printf "%-12s size=%-9s %7.2fs  %8d KB%s\n" "$w" "$s" "$e" "$m" "$flag"
done
