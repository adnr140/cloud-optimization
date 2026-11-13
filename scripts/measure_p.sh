#!/usr/bin/env bash
# measure_p.sh — re-measure p_ij on the CPU platform the VMs have TODAY (E2 does not guarantee one).
# Usage: scripts/measure_p.sh OUTDIR       (VMs must be RUNNING and deployed: deploy_all.sh)
# 1. platform of every VM: cpuPlatform (API) + lscpu model and cores/threads (guest)  -> OUTDIR/platform.txt
# 2. each of the 12 measured (workload,size) pairs, ALONE, RUNS times, on one VM of each type
#    (vm1 = e2-standard-2, vm2 = e2-medium), the two VMs in parallel, one SSH per VM -> OUTDIR/p_raw.csv
# 3. mean per pair -> data/p_matrix_now.csv (task,gce_std2_now,gce_medium_now) and data/vms_now.csv
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=../config/gcp.env
source "$ROOT/config/gcp.env"
OUT="${1:?usage: $0 OUTDIR}"; RUNS="${RUNS:-2}"; mkdir -p "$OUT"
STD2="${STD2_VM:-cloudopt-vm1}"; MEDIUM="${MEDIUM_VM:-cloudopt-vm2}"

{ for vm in $VMS; do
    echo "== $vm  $(gcloud compute instances describe "$vm" --project "$PROJECT_ID" --zone "$ZONE" \
          --format='value(machineType.basename(),cpuPlatform)' | tr '\t' ' ')"
    gcloud compute ssh "$vm" --project "$PROJECT_ID" --zone "$ZONE" --quiet \
      --command "lscpu | grep -E '^(Model name|CPU\(s\)|Thread\(s\) per core|Core\(s\) per socket|CPU max MHz)'" </dev/null
  done; } | tee "$OUT/platform.txt"

pairs="$(tail -n +2 "$ROOT/data/p_matrix.csv" | cut -d, -f1 | tr '\n' ' ')"
read -r -d '' remote <<REMOTE || true
cd ~/cloud-optimization && ./bin/cpu_task --size 1000000 >/dev/null
for p in $pairs; do w=\${p%%:*}; s=\${p##*:}
  for r in \$(seq 1 $RUNS); do echo "\$w,\$s,\$r,\$(./bin/\$w --size \$s | grep -o '"runtime_s":[0-9.]*' | cut -d: -f2)"; done
done
REMOTE
echo "measuring 12 tasks x $RUNS runs alone on $STD2 and $MEDIUM (in parallel)..."
for vm in "$STD2" "$MEDIUM"; do
  gcloud compute ssh "$vm" --project "$PROJECT_ID" --zone "$ZONE" --quiet --command "$remote" </dev/null \
    | sed "s/^/$vm,/" >"$OUT/p_$vm.csv" &
done
wait
{ echo vm,workload,size,run,runtime_s; cat "$OUT/p_$STD2.csv" "$OUT/p_$MEDIUM.csv"; } >"$OUT/p_raw.csv"
n=$(($(wc -l <"$OUT/p_raw.csv") - 1)); (( n == 24 * RUNS )) || { echo "measure_p.sh: ERROR: $n measures, expected $((24 * RUNS))" >&2; exit 1; }
awk -F, -v s="$STD2" -v m="$MEDIUM" 'NR>1 { k=$2":"$3; if (!(k in seen)) { seen[k]=1; ord[++n]=k }
       sum[$1,k]+=$5; cnt[$1,k]++ }
     END { print "task,gce_std2_now,gce_medium_now"
           for (i=1;i<=n;i++) { k=ord[i]; printf "%s,%.3f,%.3f\n", k, sum[s,k]/cnt[s,k], sum[m,k]/cnt[m,k] } }' \
  "$OUT/p_raw.csv" >"$ROOT/data/p_matrix_now.csv"
{ echo vm,machine_type,ram_mb,p_column,eff_cores
  echo "cloudopt-vm1,e2-standard-2,8192,gce_std2_now,1.25"
  echo "cloudopt-vm2,e2-medium,4096,gce_medium_now,1.25"
  echo "cloudopt-vm3,e2-medium,4096,gce_medium_now,1.25"; } >"$ROOT/data/vms_now.csv"
cp "$ROOT/data/p_matrix_now.csv" "$ROOT/data/vms_now.csv" "$OUT/"
echo "== p measured today (s, mean of $RUNS runs alone)"; sed "s/,/\t/g" "$ROOT/data/p_matrix_now.csv"
