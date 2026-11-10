#!/usr/bin/env bash
# machine_info.sh — record the execution environment in data/machine_<tag>.txt
# Usage: scripts/machine_info.sh [tag]   (default: local; TD2: cloud_vm1)
# On a Compute Engine VM it also reads the metadata server (instance name, zone, machine type, CPU platform).
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TAG="${1:-local}"
OUT="$ROOT/data/machine_${TAG}.txt"; mkdir -p "$ROOT/data"
MD=http://metadata.google.internal/computeMetadata/v1/instance
md() { curl -sf -m 2 -H "Metadata-Flavor: Google" "$MD/$1" 2>/dev/null | awk -F/ '{print $NF}'; }
sec() { echo; echo "===== $1"; shift; "$@" 2>&1; }
{
  echo "# Execution environment [$TAG] — generated $(date -Is) by scripts/machine_info.sh"
  echo
  if [[ -n "$(md name)" ]]; then   # only answers on Compute Engine
    echo "gce_instance:  $(md name)"
    echo "gce_zone:      $(md zone)"
    echo "gce_machine:   $(md machine-type)"
    echo "gce_cpu_platform: $(curl -sf -m 2 -H 'Metadata-Flavor: Google' "$MD/cpu-platform")"
    echo "gce_image:     $(md image)"
  fi
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
