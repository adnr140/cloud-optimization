#!/usr/bin/env bash
# pmatrix.sh — build the p_ij matrix (mean runtime of task i on machine j) from the per-machine profiles.
# Usage: scripts/pmatrix.sh <tag1> <tag2> ...   e.g. scripts/pmatrix.sh local cloud_vm1 cloud_vm1_std2
# Writes data/p_matrix.csv (task,<tag1>,<tag2>,...) — the scheduler input (CM3/CM4 notation p_ij)
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
(( $# >= 1 )) || { echo "usage: pmatrix.sh <tag>..." >&2; exit 1; }
files=(); for t in "$@"; do f="$ROOT/data/workload_profile_$t.csv"; [[ -s "$f" ]] || { echo "missing $f" >&2; exit 1; }; files+=("$f"); done
OUT="$ROOT/data/p_matrix.csv"
awk -F, -v hdr="$(IFS=,; echo "$*")" '
  FNR==1 {j++; next}
  { k=$1":"$2; if(!(k in seen)){seen[k]=1; ord[++n]=k}; p[k,j]=$4 }
  END { print "task," hdr
        for(i=1;i<=n;i++){ line=ord[i]; for(m=1;m<=j;m++) line=line "," ((ord[i],m) in p ? p[ord[i],m] : "NA"); print line } }' "${files[@]}" > "$OUT"
(command -v column >/dev/null && column -s, -t "$OUT") || cat "$OUT"; echo "written: $OUT"
