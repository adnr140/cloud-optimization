#!/usr/bin/env bash
# deploy_all.sh — TD3 Part 2: put the SAME workload binaries on every VM of $VMS, then smoke-test them.
# Usage: scripts/deploy_all.sh          (VMS="cloudopt-vm2" scripts/deploy_all.sh for one VM)
# 1. build static linux/amd64 binaries ONCE on the controller (make build, CGO off)
# 2. for each VM: mkdir ~/cloud-optimization/bin, scp bin/*, compare md5 with the local ones,
#    run every workload once with a tiny size. Stops at the first VM that fails.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=../config/gcp.env
source "$ROOT/config/gcp.env"
cd "$ROOT"
CGO_ENABLED=0 GOOS=linux GOARCH=amd64 make -B build >/dev/null
file bin/* | grep -v 'statically linked' && { echo "deploy_all.sh: ERROR: a binary is not static" >&2; exit 1; }
local_md5="$(cd bin && md5sum * | sort)"
echo "== local binaries"; echo "$local_md5"
for vm in $VMS; do
  echo "== $vm"
  gcloud compute ssh "$vm" --project "$PROJECT_ID" --zone "$ZONE" --quiet --command "mkdir -p ~/cloud-optimization/bin" </dev/null
  gcloud compute scp bin/* "$vm":~/cloud-optimization/bin/ --project "$PROJECT_ID" --zone "$ZONE" --quiet </dev/null
  remote_md5="$(gcloud compute ssh "$vm" --project "$PROJECT_ID" --zone "$ZONE" --quiet \
    --command "cd ~/cloud-optimization/bin && md5sum * | sort" </dev/null)"
  [[ "$remote_md5" == "$local_md5" ]] || { echo "deploy_all.sh: ERROR: md5 differ on $vm" >&2; echo "$remote_md5" >&2; exit 1; }
  echo "md5 identical to local"
  gcloud compute ssh "$vm" --project "$PROJECT_ID" --zone "$ZONE" --quiet --command "cd ~/cloud-optimization && hostname &&
    ls -lh bin && ./bin/cpu_task --size 100000 && ./bin/matrix_task --size 100 &&
    ./bin/memory_task --size 64 && ./bin/sort_task --size 100000" </dev/null
done
echo "deployed and smoke-tested on: $VMS"
