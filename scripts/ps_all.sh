#!/usr/bin/env bash
# ps_all.sh — TD3 Part 9: list the workload processes running right now on every VM of $VMS.
# Usage: scripts/ps_all.sh            (one SSH per VM, all in parallel, then a single wait)
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=../config/gcp.env
source "$ROOT/config/gcp.env"
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
echo "# ps snapshot $(date -Is)"
for vm in $VMS; do
  gcloud compute ssh "$vm" --project "$PROJECT_ID" --zone "$ZONE" --quiet \
    --command "ps --no-headers -o pid,etimes,pcpu,rss,args -C cpu_task,matrix_task,memory_task,sort_task || echo '(no workload running)'" \
    </dev/null >"$tmp/$vm" 2>/dev/null &
done
wait
for vm in $VMS; do
  n=$(grep -cE '^ *[0-9]+ ' "$tmp/$vm" || true)
  echo "== $vm : $n workload process(es)   [PID ELAPSED_S %CPU RSS_KB COMMAND]"
  cat "$tmp/$vm"
done
