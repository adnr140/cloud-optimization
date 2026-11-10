#!/usr/bin/env bash
# analyze.sh — statistics computed ONLY at analysis time, from the raw CSV.
# Usage: scripts/analyze.sh [data/benchmark_<tag>.csv]   (default: local)
#   results/summary_<tag>.md          human-readable table (mean, std, CV, min, max, RSS, scaling)
#   data/workload_profile_<tag>.csv   machine-readable profile, reused later as task estimates p_ij, m_i
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CSV="${1:-$ROOT/data/benchmark_local.csv}"
[[ -s "$CSV" ]] || { echo "analyze.sh: ERROR: $CSV missing or empty" >&2; exit 1; }
mkdir -p "$ROOT/results"
TAG="$(basename "$CSV" .csv)"; TAG="${TAG#benchmark_}"
PROFILE="$ROOT/data/workload_profile_${TAG}.csv"
SUMMARY="$ROOT/results/summary_${TAG}.md"

# one line per (workload,size): n mean std(sample) cv min max rss_mean rss_max
tail -n +2 "$CSV" | sort -t, -k1,1 -k2,2n | awk -F, '
  { k=$1","$2; if(!(k in n)) ord[++m]=k; n[k]++; s[k]+=$4; q[k]+=$4*$4; r[k]+=$5
    if(!(k in mn)||$4<mn[k]) mn[k]=$4; if($4>mx[k]) mx[k]=$4; if($5>rx[k]) rx[k]=$5 }
  END { for(i=1;i<=m;i++){k=ord[i]; mu=s[k]/n[k]
          v=(n[k]>1)?(q[k]-n[k]*mu*mu)/(n[k]-1):0; if(v<0)v=0; sd=sqrt(v)
          printf "%s,%d,%.3f,%.3f,%.1f,%.2f,%.2f,%.0f,%d\n",k,n[k],mu,sd,(mu>0?100*sd/mu:0),mn[k],mx[k],r[k]/n[k],rx[k] } }' \
  > "$PROFILE.tmp"

{ echo "workload,size,n_runs,mean_runtime_s,std_runtime_s,cv_pct,min_runtime_s,max_runtime_s,mean_max_rss_kb,max_max_rss_kb"
  cat "$PROFILE.tmp"; } > "$PROFILE"

{
  echo "# Benchmark summary — $TAG"
  echo
  echo "Source: \`$(basename "$CSV")\` ($(($(wc -l < "$CSV") - 1)) raw runs). Machine: see \`data/machine_${TAG}.txt\`."
  echo
  echo "| workload | size | n | mean (s) | std (s) | CV % | min–max (s) | mean RSS (MB) | x size | x time | exponent k (t ∝ size^k) |"
  echo "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
  awk -F, '{ if($1==pw){ xs=$2/ps; xt=($4>0&&pt>0)?$4/pt:0; k=(xt>0)?log(xt)/log(xs):0
               g=sprintf("%.2f | %.2f | %.2f", xs, xt, k) } else g="– | – | –"
             printf "| %s | %s | %d | %.3f | %.3f | %.1f | %.2f–%.2f | %.1f | %s |\n",$1,$2,$3,$4,$5,$6,$7,$8,$9/1024,g
             pw=$1; ps=$2; pt=$4 }' "$PROFILE.tmp"
  echo
  echo "*x size / x time*: ratio to the previous size of the same workload. *k*: empirical growth exponent"
  echo "(k≈1 linear, k≈3 cubic). CV = std/mean, measures run-to-run variability."
} > "$SUMMARY"
rm -f "$PROFILE.tmp"
cat "$SUMMARY"
echo; echo "written: $SUMMARY and $PROFILE"
if python3 -c 'import matplotlib' 2>/dev/null; then python3 "$ROOT/scripts/plot.py" "$CSV" "$ROOT/results" "$TAG"; else echo "(matplotlib absent: plots skipped)"; fi
