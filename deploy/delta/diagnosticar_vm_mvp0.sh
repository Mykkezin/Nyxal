#!/usr/bin/env bash
# Read-only diagnostics for a failed DELTA MVP-0 virt-install attempt.
# Does not alter libvirt domains, disks, permissions, services, or repository data.
set -uo pipefail

VM_NAME="${NYXOS_DELTA_VM_NAME:-delta-mvp0}"
POOL="${NYXOS_DELTA_VM_POOL:-default}"
CONFIGURED_STORAGE="${NYXOS_DELTA_VM_STORAGE:-${NYXOS_VPS_STORAGE:-${HOME}/NyxOS/VPS}}"
DEDICATED_STORAGE="${NYXOS_DELTA_STORAGE_ROOT:-/var/lib/libvirt/images}/delta-mvp0-storage"
LEGACY_STORAGE="${HOME}/NyxOS/VPS"

section() { printf '\n=== %s ===\n' "$1"; }
has_cmd() { command -v "$1" >/dev/null 2>&1; }

section 'Host and storage capacity'
printf 'User: %s\nHome: %s\n' "$(id -un)" "$HOME"
for storage in "$CONFIGURED_STORAGE" "$DEDICATED_STORAGE" "$LEGACY_STORAGE"; do
  [[ -n "$storage" ]] || continue
  printf '\nStorage candidate: %s\n' "$storage"
  df -h "$storage" 2>/dev/null || true
  if [[ -e "$storage" || -L "$storage" ]]; then
    ls -ldh -- "$storage" 2>/dev/null || true
  else
    echo 'PATH_ABSENT=yes'
  fi
done

section 'Previous VM definition (read-only)'
DOMAIN_STATE="unknown"
DOMAIN_LIST=""
if ! has_cmd virsh; then
  echo 'DOMAIN_EXISTS=unknown'
  echo 'DOMAIN_CHECK_REASON=virsh_not_installed'
else
  if virsh -c qemu:///system dominfo "$VM_NAME" >/dev/null 2>&1; then
    DOMAIN_STATE="yes"
  else
    # A failed dominfo is not proof of absence: it can also mean connection or
    # permission failure. Only a successful full listing can prove absence.
    if DOMAIN_LIST="$(virsh -c qemu:///system list --all --name 2>&1)"; then
      if printf '%s\n' "$DOMAIN_LIST" | grep -Fxq -- "$VM_NAME"; then
        DOMAIN_STATE="yes"
      else
        DOMAIN_STATE="no"
      fi
    else
      DOMAIN_STATE="unknown"
      echo 'DOMAIN_CHECK_REASON=libvirt_list_failed'
      printf '%s\n' "$DOMAIN_LIST"
    fi
  fi

  printf 'DOMAIN_EXISTS=%s\n' "$DOMAIN_STATE"
  if [[ "$DOMAIN_STATE" == "yes" ]]; then
    virsh -c qemu:///system dominfo "$VM_NAME" 2>&1 || true
    echo
    virsh -c qemu:///system domblklist "$VM_NAME" --details 2>&1 || true
    echo
    virsh -c qemu:///system domstate "$VM_NAME" 2>&1 || true
  elif [[ "$DOMAIN_STATE" == "no" ]]; then
    echo 'A ausência foi confirmada por uma listagem bem-sucedida de todos os domínios.'
  else
    echo 'ATENCAO: estado indeterminado. Não crie outra VM nem remova artefatos até resolver conexão/permissões do libvirt.'
  fi

  echo
  virsh -c qemu:///system list --all 2>&1 || true
fi


section 'QEMU guest agent channel (read-only)'
GUEST_AGENT_CHANNEL="unknown"
GUEST_AGENT_PING="not_attempted"
if [[ "${DOMAIN_STATE}" == "yes" ]] && has_cmd virsh; then
  DOMAIN_XML=""
  if DOMAIN_XML="$(virsh -c qemu:///system dumpxml "$VM_NAME" 2>/dev/null)"; then
    if has_cmd python3; then
      if GUEST_AGENT_CHANNEL="$(printf '%s' "$DOMAIN_XML" | python3 -c '
import sys
import xml.etree.ElementTree as ET
try:
    root = ET.fromstring(sys.stdin.read())
except ET.ParseError:
    raise SystemExit(2)
name = "org.qemu.guest_agent.0"
present = any(
    (target := channel.find("target")) is not None
    and target.attrib.get("name") == name
    for channel in root.findall("./devices/channel")
)
print("present" if present else "absent")
' 2>/dev/null)"; then
      else
        GUEST_AGENT_CHANNEL="unknown"
        echo 'GUEST_AGENT_CHANNEL_REASON=xml_parse_failed'
      fi
    else
      echo 'GUEST_AGENT_CHANNEL_REASON=python3_not_installed'
    fi
  else
    echo 'GUEST_AGENT_CHANNEL_REASON=domain_xml_unavailable'
  fi

  if [[ "$GUEST_AGENT_CHANNEL" == "present" ]]; then
    DOMAIN_RUNTIME_STATE="$(virsh -c qemu:///system domstate "$VM_NAME" 2>/dev/null || true)"
    if [[ "$DOMAIN_RUNTIME_STATE" == "running" ]]; then
      # guest-ping is a read-only QEMU Guest Agent RPC. No service is restarted
      # and no command is executed inside the guest beyond this health probe.
      if virsh -c qemu:///system qemu-agent-command "$VM_NAME" \
        '{"execute":"guest-ping"}' --timeout 5 >/dev/null 2>&1; then
        GUEST_AGENT_PING="success"
      else
        GUEST_AGENT_PING="failed"
      fi
    else
      GUEST_AGENT_PING="not_running"
    fi
  fi
else
  if [[ "$DOMAIN_STATE" != "yes" ]]; then
    echo "GUEST_AGENT_CHECK_REASON=domain_not_confirmed_present"
  else
    echo "GUEST_AGENT_CHECK_REASON=virsh_not_installed"
  fi
fi
printf 'GUEST_AGENT_CHANNEL=%s\n' "$GUEST_AGENT_CHANNEL"
printf 'GUEST_AGENT_PING=%s\n' "$GUEST_AGENT_PING"

section 'VM storage pool (read-only)'
if has_cmd virsh && virsh -c qemu:///system pool-info "$POOL" >/dev/null 2>&1; then
  virsh -c qemu:///system pool-info "$POOL" 2>&1 || true
  pool_xml="$(virsh -c qemu:///system pool-dumpxml "$POOL" 2>/dev/null || true)"
  if [[ -n "$pool_xml" ]] && has_cmd python3; then
    printf '%s' "$pool_xml" | python3 -c 'import sys,xml.etree.ElementTree as E; r=E.fromstring(sys.stdin.read()); print("Pool type:",r.attrib.get("type","unknown")); print("Pool path:",(r.findtext("./target/path") or "").strip())' 2>&1 || true
    pool_path="$(printf '%s' "$pool_xml" | python3 -c 'import sys,xml.etree.ElementTree as E; r=E.fromstring(sys.stdin.read()); print((r.findtext("./target/path") or "").strip())' 2>/dev/null || true)"
    if [[ -n "$pool_path" && -d "$pool_path" ]]; then
      df -h "$pool_path" 2>/dev/null || true
      ls -ldh -- "$pool_path" 2>/dev/null || true
    fi
  fi
else
  echo "POOL_EXISTS=no name=$POOL"
  if has_cmd virsh; then virsh -c qemu:///system pool-list --all 2>&1 || true; fi
fi

section 'Possible leftover files (all known storage candidates)'
for storage in "$CONFIGURED_STORAGE" "$DEDICATED_STORAGE" "$LEGACY_STORAGE"; do
  [[ -n "$storage" ]] || continue
  printf '\nStorage: %s\n' "$storage"
  for filename in \
    "${VM_NAME}.qcow2" \
    "${VM_NAME}-seed.img" \
    "${VM_NAME}-user-data.yaml" \
    "${VM_NAME}-meta-data.yaml"; do
    path="${storage%/}/${filename}"
    if [[ -e "$path" || -L "$path" ]]; then
      ls -ldh -- "$path" 2>&1 || true
    else
      printf 'ABSENT  %s\n' "$path"
    fi
  done
done

section 'QEMU account and ACL tool'
if getent passwd libvirt-qemu >/dev/null 2>&1; then
  getent passwd libvirt-qemu | cut -d: -f1,3,4
else
  echo 'libvirt-qemu account not found'
fi
if has_cmd getfacl; then
  echo 'ACL for home directory (no file contents):'
  getfacl -cp "$HOME" 2>&1 || true
else
  echo 'getfacl not installed'
fi

printf '\nDiagnostic completed. This script made no changes.\n'
