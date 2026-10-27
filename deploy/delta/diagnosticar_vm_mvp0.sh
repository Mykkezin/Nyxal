#!/usr/bin/env bash
# Read-only diagnostics for a failed DELTA MVP-0 virt-install attempt.
# Does not alter libvirt domains, disks, permissions, services, or repository data.
set -uo pipefail

VM_NAME="${NYXOS_DELTA_VM_NAME:-delta-mvp0}"
POOL="${NYXOS_DELTA_VM_POOL:-default}"
OLD_STORAGE="${NYXOS_VPS_STORAGE:-${HOME}/NyxOS/VPS"

section() { printf '\n=== %s ===\n' "$1"; }
has_cmd() { command -v "$1" >/dev/null 2>&1; }

section 'Host and storage capacity'
printf 'User: %s\nHome: %s\n' "$(id -un)" "$HOME"
df -h "$HOME" "$OLD_STORAGE" 2>/dev/null || true
if [[ -e "$OLD_STORAGE" ]]; then
  ls -ld "$HOME" "$HOME/NyxOS" "$OLD_STORAGE" 2>/dev/null || true
fi

section 'Previous VM definition (read-only)'
if has_cmd virsh && virsh -c qemu:///system dominfo "$VM_NAME" >/dev/null 2>&1; then
  echo "DOMAIN_EXISTS=yes"
  virsh -c qemu:///system dominfo "$VM_NAME" 2>&1 || true
  echo
  virsh -c qemu:///system domblklist "$VM_NAME" --details 2>&1 || true
  echo
  virsh -c qemu:///system domstate "$VM_NAME" 2>&1 || true
else
  echo "DOMAIN_EXISTS=no"
fi
echo
if has_cmd virsh; then
  virsh -c qemu:///system list --all 2>&1 || true
fi

section 'VM storage pool (read-only)'
if has_cmd virsh && virsh -c qemu:///system pool-info "$POOL" >/dev/null 2>&1; then
  virsh -c qemu:///system pool-info "$POOL" 2>&1 || true
  pool_xml="$(virsh -c qemu:///system pool-dumpxml "$POOL" 2>/dev/null || true)"
  if [[ -n "$pool_xml" ]] && has_cmd python3; then
    printf '%s' "$pool_xml" | python3 -c 'import sys,xml.etree.ElementTree as E; r=E.fromstring(sys.stdin.read()); print("Pool type:",r.attrib.get("type","unknown")); print("Pool path:",(r.findtext("./target/path") or "").strip())' 2>&1 || true
    pool_path="$(printf '%s' "$pool_xml" | python3 -c 'import sys,xml.etree.ElementTree as E; r=E.fromstring(sys.stdin.read()); print((r.findtext("./target/path") or "").strip())' 2>/dev/null || true)"
    if [[ -n "$pool_path" && -d "$pool_path" ]]; then
      df -h "$pool_path" 2>/dev/null || true
      ls -ld "$pool_path" 2>/dev/null || true
    fi
  fi
else
  echo "POOL_EXISTS=no name=$POOL"
  if has_cmd virsh; then virsh -c qemu:///system pool-list --all 2>&1 || true; fi
fi

section 'Possible leftover files from failed attempt'
for path in   "${OLD_STORAGE%/}/${VM_NAME}.qcow2"   "${OLD_STORAGE%/}/${VM_NAME}-seed.img"   "${OLD_STORAGE%/}/${VM_NAME}-user-data.yaml"   "${OLD_STORAGE%/}/${VM_NAME}-meta-data.yaml"; do
  if [[ -e "$path" || -L "$path" ]]; then
    ls -ldh -- "$path" 2>&1 || true
  else
    printf 'ABSENT  %s\n' "$path"
  fi
done

section 'QEMU account and ACL tool'
if getent passwd libvirt-qemu >/dev/null 2>&1; then
  getent passwd libvirt-qemu | cut -d: -f1,3,4
else
  echo 'libvirt-qemu account not found'
fi
if has_cmd getfacl; then
  echo "ACL for home directory (no file contents):"
  getfacl -cp "$HOME" 2>&1 || true
else
  echo 'getfacl not installed'
fi

printf '\nDiagnostic completed. This script made no changes.\n'
