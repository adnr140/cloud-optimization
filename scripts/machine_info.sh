#!/usr/bin/env bash
# machine_info.sh — record the execution environment in data/machine_local.txt
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="$ROOT/data/machine_local.txt"; mkdir -p "$ROOT/data"
sec() { echo; echo "===== $1"; shift; "$@" 2>&1; }
{
  echo "# Local execution environment — generated $(date -Is) by scripts/machine_info.sh"
  echo
  echo "os:            $( (. /etc/os-release && echo "$PRETTY_NAME") 2>/dev/null || uname -s)"
  echo "kernel:        $(uname -r)"
  echo "cpu_model:     $(lscpu | awk -F: '/Model name/{gsub(/^ +/,"",$2);print $2; exit}')"
  echo "logical_cpus:  $(nproc)"
  echo "threads/core:  $(lscpu | awk -F: '/Thread\(s\) per core/{gsub(/ /,"",$2);print $2}')"
  echo "cores/socket:  $(lscpu | awk -F: '/Core\(s\) per socket/{gsub(/ /,"",$2);print $2}')"
  echo "sockets:       $(lscpu | awk -F: '/Socket\(s\)/{gsub(/ /,"",$2);print $2}')"
  echo "ram_total:     $(free -h | awk '/Mem:/{print $2}')"
  echo "ram_available: $(free -h | awk '/Mem:/{print $7}')"
  echo "virtualized:   $(systemd-detect-virt 2>/dev/null || lscpu | awk -F: '/Hypervisor vendor/{gsub(/^ +/,"",$2);print $2}' || echo unknown)"
  echo "cpu_governor:  $(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null || echo n/a)"
  echo "go_version:    $(go version 2>/dev/null || echo 'go not found')"
  echo "gnu_time:      $(/usr/bin/time --version 2>&1 | head -n1)"
  sec "uname -a" uname -a
  sec "lscpu" lscpu
  sec "nproc" nproc
  sec "free -h" free -h
  sec "lsblk" lsblk
  sec "df -h ." df -h "$ROOT"
} > "$OUT"
echo "written: $OUT"; sed -n '1,16p' "$OUT"
