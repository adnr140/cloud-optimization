#!/usr/bin/env bash
# estimate_alloc.sh — TD4 Part 6: what would this allocation cost, according to our TD2 measurements?
# Usage: scripts/estimate_alloc.sh ALLOCATION_CSV
# NOT a scheduler and NOT a measurement: a reading of an allocation with the information Round-Robin ignores.
# Per VM: number of tasks, sum of p_ij (data/p_matrix.csv, column chosen by data/vm_profile.csv),
# longest task, peak RAM if all tasks run together (sum of RSS, data/workload_profile_cloud_vm1_std2.csv;
# RSS is the same on every machine, D22) and a rough finish time:
#   est_s = SSH (3 s, TD3) + max( longest p_ij , sum p_ij / vCPU )   <- optimistic: perfect sharing of the vCPUs
# The real duration is longer when tasks > vCPU (TD3: cpu_task 10M 9.6 s alone -> 14.6 s with 2 others).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
A="${1:?usage: $0 ALLOCATION_CSV}"; SSH_S="${SSH_S:-3}"
awk -F, -v ssh="$SSH_S" '
  { gsub(/\r/,"") }
  FILENAME ~ /vm_profile/  { if (FNR>1) { col[$1]=$5; vcpu[$1]=$3; ram[$1]=$4; type[$1]=$2 } next }
  FILENAME ~ /p_matrix/    { if (FNR==1) { for(i=2;i<=NF;i++) ci[$i]=i; next } for (c in ci) p[$1,c]=$(ci[c]); next }
  FILENAME ~ /workload_profile/ { if (FNR>1) rss[$1":"$2]=$9/1024; next }
  FNR==1 { next }
  NF {
    k=$2":"$3; v=$4
    if (!(v in col)) { print "unknown VM " v " (add it to data/vm_profile.csv)" > "/dev/stderr"; exit 2 }
    t=p[k,col[v]]; if (t=="" || t=="NA") { print "no p_ij for " k " on " col[v] > "/dev/stderr"; exit 2 }
    if (!(v in n)) ord[++nv]=v
    n[v]++; s[v]+=t; if (t>mx[v]) mx[v]=t; m[v]+=rss[k]; list[v]=list[v] " " $1
  }
  END {
    printf "%-13s %-13s %5s %9s %9s %10s %8s  %s\n", "vm","type","tasks","sum_p_s","max_p_s","ram_MB","est_s","tasks"
    for (i=1;i<=nv;i++) { v=ord[i]; e=ssh+((mx[v]>s[v]/vcpu[v])?mx[v]:s[v]/vcpu[v]); if (e>best) { best=e; bv=v }
      flag=""; if (m[v]>ram[v]) { flag="  <- RAM OVER CAPACITY: infeasible"; bad++ }
      printf "%-13s %-13s %5d %9.1f %9.1f %5.0f/%-4d %8.1f %s%s\n", v, type[v], n[v], s[v], mx[v], m[v], ram[v], e, list[v], flag }
    printf "estimated makespan: %.1f s (bottleneck %s)\n", best, bv
    if (bad) { print "INFEASIBLE: " bad " VM(s) would run out of RAM (do NOT run this allocation)"; exit 1 }
  }' "$ROOT/data/vm_profile.csv" "$ROOT/data/p_matrix.csv" "$ROOT/data/workload_profile_cloud_vm1_std2.csv" "$A"
