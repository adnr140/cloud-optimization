#!/usr/bin/env bash
# burst_study.sh — measure CPU bursting of the shared-core e2-medium against the e2-standard-2.
# Usage: scripts/burst_study.sh [OUTDIR]        (VMs RUNNING and deployed: deploy_all.sh). ~36 min.
# Unit of work: cpu_task --size $UNIT (CPU only, no memory effect), run in a loop by S "streams"
# (S parallel loops = S busy vCPUs). Every unit logs its start/end on the VM clock; a sampler logs
# the cumulative CPU steal time of /proc/stat every second (time the hypervisor took the vCPU away).
#   phase 0  platform of every VM
#   phase 1  charge: all VMs idle CHARGE s (a shared-core VM earns credits while it is under its baseline)
#   phase 2  depletion, in parallel for DEPLETE s: vm2 e2-medium 2 streams, vm3 e2-medium 1 stream,
#            vm1 e2-standard-2 2 streams (control: no bursting)
#   phase 3  recovery: idle 60 / 180 / 600 s, then a PROBE s probe on vm2 (2 streams) and vm3 (1 stream)
#            (and vm1 1 stream: single-thread reference of the e2-standard-2)
# Output: OUTDIR/platform.txt, OUTDIR/burst_raw.csv (phase,vm,kind,a,b,c)
#   kind=run : a=stream b=start c=end   (epoch s, VM clock)      kind=stat : a=time b=steal c=total (jiffies)
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=../config/gcp.env
source "$ROOT/config/gcp.env"
OUT="${1:-$ROOT/results/burst/session_$(date +%Y%m%d_%H%M)}"; mkdir -p "$OUT"
CHARGE="${CHARGE:-600}" DEPLETE="${DEPLETE:-420}" PROBE="${PROBE:-90}" UNIT="${UNIT:-3000000}"
RECOVER="${RECOVER:-60 180 600}"
echo "burst study -> $OUT  (charge ${CHARGE}s, depletion ${DEPLETE}s, recovery probes after: $RECOVER s)"

# phase 0
{ for vm in $VMS; do
    echo "== $vm  $(gcloud compute instances describe "$vm" --project "$PROJECT_ID" --zone "$ZONE" \
          --format='value(machineType.basename(),cpuPlatform)' | tr '\t' ' ')"
    gcloud compute ssh "$vm" --project "$PROJECT_ID" --zone "$ZONE" --quiet \
      --command "lscpu | grep -E '^(Model name|CPU\(s\)|Thread\(s\) per core|Core\(s\) per socket)'" </dev/null
  done; echo "unit: cpu_task --size $UNIT"; } | tee "$OUT/platform.txt"

# one load on one VM: S streams for D seconds + a steal sampler, all on the VM, in ONE ssh session
load() {  # load PHASE VM STREAMS SECONDS
  local phase=$1 vm=$2 s=$3 d=$4 remote
  read -r -d '' remote <<REMOTE || true
cd ~/cloud-optimization
( end=\$((SECONDS+$d)); while [ \$SECONDS -lt \$end ]; do
    echo "stat,\$(date +%s.%N),\$(head -1 /proc/stat | awk '{print \$9","\$2+\$3+\$4+\$5+\$6+\$7+\$8+\$9}')"; sleep 1; done ) &
for k in \$(seq 1 $s); do ( end=\$((SECONDS+$d)); while [ \$SECONDS -lt \$end ]; do
    t0=\$(date +%s.%N); ./bin/cpu_task --size $UNIT >/dev/null; echo "run,\$k,\$t0,\$(date +%s.%N)"; done ) & done
wait
REMOTE
  gcloud compute ssh "$vm" --project "$PROJECT_ID" --zone "$ZONE" --quiet --ssh-flag=-oServerAliveInterval=30 \
    --command "$remote" </dev/null | sed "s/^/$phase,$vm,/" >"$OUT/raw_${phase}_$vm.csv"
}   # one file per load: 3 loads appending to one file in parallel interleave their lines (first session)
echo "[$(date +%T)] phase 1: all VMs idle ${CHARGE}s (credits accumulate)"; sleep "$CHARGE"
echo "[$(date +%T)] phase 2: depletion ${DEPLETE}s: vm2 2 streams, vm3 1 stream, vm1 2 streams"
load deplete cloudopt-vm2 2 "$DEPLETE" & load deplete cloudopt-vm3 1 "$DEPLETE" & load deplete cloudopt-vm1 2 "$DEPLETE" &
wait
for idle in $RECOVER; do
  echo "[$(date +%T)] phase 3: idle ${idle}s, then probe ${PROBE}s"; sleep "$idle"
  load "recover_$idle" cloudopt-vm2 2 "$PROBE" & load "recover_$idle" cloudopt-vm3 1 "$PROBE" &
  load "recover_$idle" cloudopt-vm1 1 "$PROBE" &
  wait
done
{ echo "phase,vm,kind,a,b,c"; cat "$OUT"/raw_*.csv; } >"$OUT/burst_raw.csv" && rm -f "$OUT"/raw_*.csv
echo "[$(date +%T)] done: $(($(wc -l <"$OUT/burst_raw.csv") - 1)) lines -> $OUT/burst_raw.csv"
python3 "$ROOT/scripts/burst_analysis.py" "$OUT" || echo "analysis failed: run python3 scripts/burst_analysis.py $OUT"
python3 "$ROOT/scripts/burst_cost.py" "$OUT" $(ls -d "$ROOT"/results/project/session_* 2>/dev/null | tail -1) \
  || echo "cost analysis failed: run make burst-cost"
