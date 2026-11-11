#!/usr/bin/env bash
# run_task.sh — TD3: execute ONE task on ONE VM, collect its stdout/stderr locally.
# Usage: scripts/run_task.sh TASK_ID WORKLOAD SIZE VM ZONE [OUTDIR]
#   e.g. scripts/run_task.sh T1 cpu_task 500000 cloudopt-vm1 europe-west1-b results/td3/test
# Writes, in OUTDIR (default results/):
#   TASK_ID.out   stdout of the workload (its JSON line)
#   TASK_ID.err   stderr of gcloud/ssh and of the workload (errors stay visible here)
#   TASK_ID.meta  task_id, workload, size, vm, remote_host (hostname seen by the remote shell),
#                 exit_code, launch/end time on the controller (epoch s, only to show overlap)
# Exit status = exit status of the remote command (255 = ssh itself failed).
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=../config/gcp.env
source "$ROOT/config/gcp.env"
die() { echo "run_task.sh: ERROR: $*" >&2; exit 2; }

[[ $# -ge 5 ]] || die "usage: $0 TASK_ID WORKLOAD SIZE VM ZONE [OUTDIR]"
TASK_ID="$1" WORKLOAD="$2" SIZE="$3" VM="$4" TZONE="$5" OUTDIR="${6:-$ROOT/results}"
for v in TASK_ID WORKLOAD SIZE VM TZONE; do [[ -n "${!v}" ]] || die "$v is empty"; done
# These values are pasted into a remote shell command: accept only safe characters (no injection).
[[ "$TASK_ID"  =~ ^[A-Za-z0-9_-]+$ ]] || die "invalid task_id '$TASK_ID'"
[[ "$WORKLOAD" =~ ^[a-z_]+$ ]]        || die "invalid workload '$WORKLOAD'"
[[ "$SIZE"     =~ ^[0-9]+$ ]]         || die "size must be a non-negative integer, got '$SIZE'"
[[ "$VM"       =~ ^[a-z0-9-]+$ ]]     || die "invalid vm '$VM'"
mkdir -p "$OUTDIR"

out="$OUTDIR/$TASK_ID.out" err="$OUTDIR/$TASK_ID.err" raw="$OUTDIR/$TASK_ID.raw"
launch=$(date +%s.%N)
# One task = one SSH session. First line printed remotely = hostname (proof of placement),
# then the workload itself. stdin from /dev/null: gcloud/ssh must never eat the caller's stdin.
gcloud compute ssh "$VM" --project "$PROJECT_ID" --zone "$TZONE" --quiet \
  --ssh-flag=-oServerAliveInterval=30 \
  --command "hostname; cd ~/cloud-optimization && exec ./bin/$WORKLOAD --size $SIZE" \
  </dev/null >"$raw" 2>"$err"
rc=$?
end=$(date +%s.%N)

remote_host="$(head -n1 "$raw")"
tail -n +2 "$raw" >"$out" && rm -f "$raw"
printf 'task_id=%s\nworkload=%s\nsize=%s\nvm=%s\nremote_host=%s\nexit_code=%s\nlaunch_epoch=%s\nend_epoch=%s\n' \
  "$TASK_ID" "$WORKLOAD" "$SIZE" "$VM" "$remote_host" "$rc" "$launch" "$end" >"$OUTDIR/$TASK_ID.meta"

if [[ $rc -eq 0 ]]; then echo "[$(date +%T)] done   $TASK_ID on $VM"
else echo "[$(date +%T)] FAILED $TASK_ID on $VM (exit $rc, see $err)" >&2; fi
exit "$rc"
