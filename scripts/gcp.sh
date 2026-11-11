#!/usr/bin/env bash
# gcp.sh — TD2: every Compute Engine action of the project, driven by config/gcp.env.
# Usage: scripts/gcp.sh <command>        (override any variable: VM_NAME=cloudopt-vm2 scripts/gcp.sh create)
#   preflight  check gcloud, active account, project, Compute Engine API
#   explore    zone, E2 machine types, machine-type and image details  -> data/gcp_explore_<TAG>.txt
#   create     create the VM (no-op if it already exists)
#   describe   status, machine type, disk, network, IPs                -> data/vm_<TAG>.txt
#   deploy     copy the committed project (git archive HEAD) to the VM, records the commit
#   setup      install Go + GNU time + make on the VM, build the workloads, record the machine
#   bench      run the full campaign on the VM (non-interactive)       -> data/benchmark_<TAG>.csv on the VM
#   fetch      copy CSV, machine description and campaign metadata back to data/
#   ssh        interactive shell on the VM          run "<cmd>"  one remote command
#   label      add the course labels to an existing VM
#   resize <type>  stop, change the machine type, start (TD Part 15)
#   stop | start | status                            lifecycle
#   delete     delete the VM (gcloud asks for confirmation; boot disk auto-delete is checked first)
#   inventory  list every billable resource left in the project (instances, disks, IPs, snapshots)
#   start-all | stop-all | status-all   TD3: same lifecycle for every VM of $VMS (config/gcp.env)
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=../config/gcp.env
source "$ROOT/config/gcp.env"
die() { echo "gcp.sh: ERROR: $*" >&2; exit 1; }
say() { echo "== $*"; }
[[ "$PROJECT_ID" != "CHANGE_ME" ]] || die "set PROJECT_ID in config/gcp.env (or: PROJECT_ID=... scripts/gcp.sh ...)"
command -v gcloud >/dev/null || die "gcloud not installed (https://cloud.google.com/sdk/docs/install) or use Cloud Shell"
P=(--project "$PROJECT_ID"); Z=(--project "$PROJECT_ID" --zone "$ZONE")
SSH_OPTS=(--ssh-flag=-oServerAliveInterval=30)
remote() { gcloud compute ssh "$VM_NAME" "${Z[@]}" "${SSH_OPTS[@]}" --command "$1"; }
# After start, RUNNING != ready: the guest OS still boots and sshd refuses connections for ~20-60 s.
wait_ssh() {
  for i in $(seq 1 12); do
    gcloud compute ssh "$VM_NAME" "${Z[@]}" --command true -- -oConnectTimeout=5 >/dev/null 2>&1 && { echo "ssh ready"; return 0; }
    echo "waiting for sshd on $VM_NAME ($i/12)..."; sleep 10
  done; die "ssh still unreachable after 2 min (try: gcloud compute ssh $VM_NAME --zone $ZONE --troubleshoot)"
}
exists() { gcloud compute instances describe "$VM_NAME" "${Z[@]}" --format='value(name)' >/dev/null 2>&1; }

case "${1:-}" in
preflight)
  gcloud --version | head -n1
  say "active account";  gcloud auth list --filter=status:ACTIVE --format='value(account)'
  say "gcloud config";   gcloud config list 2>/dev/null
  cur="$(gcloud config get-value project 2>/dev/null || true)"
  [[ "$cur" == "$PROJECT_ID" ]] || echo "WARNING: gcloud default project is '$cur', scripts use '$PROJECT_ID' explicitly"
  say "Compute Engine API"
  gcloud services list --enabled "${P[@]}" --filter='config.name=compute.googleapis.com' --format='value(config.name)' \
    | grep -q compute || die "compute.googleapis.com not enabled: gcloud services enable compute.googleapis.com --project $PROJECT_ID"
  echo "compute.googleapis.com enabled" ;;
explore)
  out="$ROOT/data/gcp_explore_${TAG}.txt"
  { echo "# generated $(date -Is) project=$PROJECT_ID zone=$ZONE"
    say "zone";          gcloud compute zones describe "$ZONE" "${P[@]}" --format='yaml(name,region,status,availableCpuPlatforms)'
    say "E2 machine types in $ZONE"
    gcloud compute machine-types list "${P[@]}" --filter="zone:($ZONE) AND name~'^e2-'" --format='table(name,guestCpus,memoryMb,isSharedCpu)'
    say "machine type $MACHINE_TYPE"
    gcloud compute machine-types describe "$MACHINE_TYPE" "${Z[@]}" --format='yaml(name,description,guestCpus,memoryMb,isSharedCpu,architecture,zone)'
    say "image family $IMAGE_FAMILY"
    gcloud compute images describe-from-family "$IMAGE_FAMILY" --project "$IMAGE_PROJECT" \
      --format='yaml(name,family,creationTimestamp,architecture,diskSizeGb,sourceDisk,status)'
  } | tee "$out"; echo "written: $out" ;;
create)
  if exists; then echo "$VM_NAME already exists in $ZONE (nothing created)"; exit 0; fi
  gcloud compute instances create "$VM_NAME" "${Z[@]}" \
    --machine-type="$MACHINE_TYPE" \
    --image-family="$IMAGE_FAMILY" --image-project="$IMAGE_PROJECT" \
    --boot-disk-size="$BOOT_DISK_SIZE" --boot-disk-type="$BOOT_DISK_TYPE" \
    --labels="$LABELS"
  gcloud compute instances list "${P[@]}" --filter="name=$VM_NAME" ;;
describe)
  out="$ROOT/data/vm_${TAG}.txt"
  { echo "# generated $(date -Is)"
    gcloud compute instances describe "$VM_NAME" "${Z[@]}" --format='yaml(
      name,status,zone.basename(),machineType.basename(),cpuPlatform,creationTimestamp,labels,
      disks[].deviceName,disks[].diskSizeGb,disks[].autoDelete,disks[].boot,
      networkInterfaces[].network.basename(),networkInterfaces[].subnetwork.basename(),
      networkInterfaces[].networkIP,networkInterfaces[].accessConfigs[].natIP,
      networkInterfaces[].accessConfigs[].type,serviceAccounts[].email,scheduling)'
    bd="$(gcloud compute instances describe "$VM_NAME" "${Z[@]}" --format='value(disks[0].source.basename())')"
    say "boot disk $bd"; gcloud compute disks describe "$bd" "${Z[@]}" --format='yaml(name,sizeGb,type.basename(),status,sourceImage.basename())'
    say "SSH firewall rules (network default)"
    gcloud compute firewall-rules list "${P[@]}" --format='table(name,network.basename(),direction,sourceRanges.list(),allowed[].map().firewall_rule().list())'
  } | tee "$out"; echo "written: $out" ;;
deploy)
  git -C "$ROOT" diff --quiet HEAD || echo "WARNING: uncommitted changes are NOT deployed (only HEAD is)"
  rev="$(git -C "$ROOT" rev-parse --short HEAD)"; tgz="$(mktemp --suffix=.tar.gz)"; trap 'rm -f "$tgz"' EXIT
  git -C "$ROOT" archive --format=tar.gz --prefix=cloud-optimization/ HEAD > "$tgz"
  gcloud compute scp "$tgz" "$VM_NAME":~/deploy.tar.gz "${Z[@]}"
  remote "rm -rf ~/cloud-optimization.prev; [ -d ~/cloud-optimization ] && mv ~/cloud-optimization ~/cloud-optimization.prev; tar xzf ~/deploy.tar.gz && rm ~/deploy.tar.gz && echo $rev > ~/cloud-optimization/DEPLOYED_COMMIT && cd ~/cloud-optimization && md5sum workloads/*.go && find . -maxdepth 2 -type f | sort | head -40"
  echo "deployed commit $rev to $VM_NAME" ;;
setup)
  remote "set -e; sudo apt-get update -qq && sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq golang-go time make file curl >/dev/null
    cd ~/cloud-optimization && go version && /usr/bin/time --version 2>&1 | head -1
    make build && ls -lh bin/ && make machine TAG=$TAG" ;;
bench)
  remote "cd ~/cloud-optimization && make bench TAG=$TAG && make analyze TAG=$TAG" ;;
fetch)
  for f in "benchmark_${TAG}.csv" "machine_${TAG}.txt" "campaign_meta_${TAG}.txt" "workload_profile_${TAG}.csv" "memprobe_${TAG}.csv"; do
    gcloud compute scp "$VM_NAME:~/cloud-optimization/data/$f" "$ROOT/data/" "${Z[@]}" || echo "WARNING: $f not fetched"
  done
  gcloud compute scp "$VM_NAME:~/cloud-optimization/results/summary_${TAG}.md" "$ROOT/results/" "${Z[@]}" || true
  ls -l "$ROOT"/data/*"${TAG}"* ;;
resize) [[ -n "${2:-}" ]] || die "usage: scripts/gcp.sh resize <machine-type>"
        gcloud compute instances stop "$VM_NAME" "${Z[@]}"
        gcloud compute instances set-machine-type "$VM_NAME" "${Z[@]}" --machine-type="$2"
        gcloud compute instances start "$VM_NAME" "${Z[@]}"; "$0" status; wait_ssh ;;
label)  gcloud compute instances add-labels "$VM_NAME" "${Z[@]}" --labels="$LABELS"; "$0" status ;;
ssh)    gcloud compute ssh "$VM_NAME" "${Z[@]}" ;;
run)    [[ -n "${2:-}" ]] || die 'usage: scripts/gcp.sh run "<command>"'; remote "$2" ;;
stop)   gcloud compute instances stop "$VM_NAME" "${Z[@]}"; "$0" status ;;
start)  gcloud compute instances start "$VM_NAME" "${Z[@]}"; "$0" status; wait_ssh ;;
status) gcloud compute instances list "${P[@]}" --filter="name=$VM_NAME" --format='table(name,zone.basename(),machineType.basename(),status,networkInterfaces[0].networkIP,networkInterfaces[0].accessConfigs[0].natIP)' ;;
delete)
  say "disks attached to $VM_NAME (autoDelete=True means deleted with the VM)"
  gcloud compute instances describe "$VM_NAME" "${Z[@]}" --format='table(disks[].deviceName,disks[].autoDelete)'
  gcloud compute instances delete "$VM_NAME" "${Z[@]}"     # interactive confirmation on purpose
  "$0" inventory ;;
inventory)
  say "instances"; gcloud compute instances list "${P[@]}"
  say "disks";     gcloud compute disks list "${P[@]}"
  say "addresses (static IPs)"; gcloud compute addresses list "${P[@]}"
  say "snapshots"; gcloud compute snapshots list "${P[@]}"
  say "images (custom)"; gcloud compute images list "${P[@]}" --no-standard-images ;;
start-all)
  # shellcheck disable=SC2086
  gcloud compute instances start $VMS "${Z[@]}"; "$0" status-all
  for v in $VMS; do VM_NAME=$v wait_ssh; done ;;
stop-all)   # shellcheck disable=SC2086
  gcloud compute instances stop $VMS "${Z[@]}"; "$0" status-all ;;
status-all)
  gcloud compute instances list "${P[@]}" --filter="name:( $VMS )" --format='table(name,zone.basename(),machineType.basename(),status,networkInterfaces[0].networkIP,networkInterfaces[0].accessConfigs[0].natIP)' ;;
*) sed -n '2,20p' "$0"; exit 1 ;;
esac
