#!/usr/bin/env bash
# DELTA MVP-0 — read-only host preflight for a bootable VM prototype.
# This script does not install packages, change services, create VMs, or write to the repo.
set -uo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd -- "${SCRIPT_DIR}/../.." && pwd)"
PASS=0
WARN=0
FAIL=0

ok()   { printf 'PASS  %s\n' "$1"; PASS=$((PASS + 1)); }
warn() { printf 'WARN  %s\n' "$1"; WARN=$((WARN + 1)); }
fail() { printf 'FAIL  %s\n' "$1"; FAIL=$((FAIL + 1)); }
info() { printf 'INFO  %s\n' "$1"; }

has_cmd() { command -v "$1" >/dev/null 2>&1; }

printf '%s\n' 'DELTA / NyxOS — VM prototype preflight (read-only)'
printf '%s\n' '=================================================='
printf 'Host: %s | Arch: %s | Kernel: %s\n' "$(uname -s)" "$(uname -m)" "$(uname -r)"

if [[ -r /etc/os-release ]]; then
  # shellcheck disable=SC1091
  . /etc/os-release
  info "Distro: ${PRETTY_NAME:-desconhecida}"
fi

# Repository structure checks only inspect existing files.
for path in README.md deploy/systemd/nyxos.target deploy/systemd/nyxal-api.service deploy/systemd/nyxos-residente.service nyxal_web_api.py; do
  if [[ -f "${ROOT}/${path}" ]]; then
    ok "Componente existente: ${path}"
  else
    fail "Componente ausente no checkout esperado: ${path}"
  fi
done

# A QEMU executable and qemu-img are the minimum tools for a manual VM spike.
if has_cmd qemu-system-x86_64 || has_cmd qemu-system-aarch64; then
  ok "Emulador QEMU encontrado ($(command -v qemu-system-x86_64 2>/dev/null || command -v qemu-system-aarch64 2>/dev/null))"
else
  fail 'QEMU não encontrado (esperado qemu-system-x86_64 ou qemu-system-aarch64)'
fi
if has_cmd qemu-img; then
  ok "qemu-img encontrado ($(command -v qemu-img))"
else
  fail 'qemu-img não encontrado'
fi

# KVM is recommended for performance, but QEMU can fall back to software emulation.
if [[ -c /dev/kvm ]]; then
  if [[ -r /dev/kvm && -w /dev/kvm ]]; then
    ok '/dev/kvm existe e o usuário atual tem acesso de leitura/escrita'
  else
    warn '/dev/kvm existe, mas o usuário atual não tem acesso completo; verificar grupo/permissões fora deste script'
  fi
else
  warn '/dev/kvm indisponível: KVM não poderá ser usado por este usuário; QEMU pode operar mais lentamente por emulação'
fi

# Read MemTotal directly from procfs so this check does not depend on the output
# of the optional free utility, localization, or an extra package.
if [[ -r /proc/meminfo ]]; then
  mem_kib="$(awk '/^MemTotal:/ {print $2; exit}' /proc/meminfo)"
  if [[ "${mem_kib:-}" =~ ^[0-9]+$ ]]; then
    mem_gib=$((mem_kib / 1024 / 1024))
    if (( mem_gib >= 8 )); then
      ok "RAM total: ${mem_gib} GiB (recomendado >= 8 GiB)"
    else
      warn "RAM total: ${mem_gib} GiB; imagem gráfica pode precisar de recursos menores"
    fi
  else
    warn 'Não foi possível interpretar MemTotal em /proc/meminfo'
  fi
else
  warn '/proc/meminfo indisponível; RAM não avaliada'
fi

if has_cmd df; then
  avail_kib="$(df -Pk "${ROOT}" | awk 'NR==2 {print $4}')"
  if [[ "${avail_kib:-}" =~ ^[0-9]+$ ]]; then
    disk_gib=$((avail_kib / 1024 / 1024))
    if (( disk_gib >= 30 )); then
      ok "Espaço livre no filesystem do checkout: ${disk_gib} GiB (recomendado >= 30 GiB)"
    else
      warn "Espaço livre: ${disk_gib} GiB; reservar espaço para imagem e snapshots antes de baixar/buildar imagens grandes"
    fi
  else
    warn 'Não foi possível medir o espaço livre do filesystem do checkout'
  fi
else
  warn 'Comando df não encontrado; espaço livre não avaliado'
fi

# Optional virtualization management and candidate image toolchains.
for tool in virsh virt-install virt-host-validate; do
  if has_cmd "$tool"; then
    ok "Ferramenta opcional disponível: ${tool}"
  else
    warn "Ferramenta opcional ausente: ${tool}"
  fi
done
if has_cmd nix; then
  ok 'Nix disponível para protótipo NixOS'
else
  warn 'Nix ausente: caminho NixOS ainda não está pronto neste host'
fi
if has_cmd podman; then
  ok 'Podman disponível para avaliar imagem baseada em bootc'
else
  warn 'Podman ausente: caminho Fedora bootc ainda não está pronto neste host'
fi
if has_cmd bootc-image-builder; then
  ok 'bootc-image-builder disponível'
else
  warn 'bootc-image-builder ausente: ferramenta de imagem Fedora bootc não detectada'
fi

printf '\nResumo: %d PASS | %d WARN | %d FAIL\n' "$PASS" "$WARN" "$FAIL"
if (( FAIL > 0 )); then
  printf '%s\n' 'RESULTADO=BLOCKED — corrija os requisitos essenciais antes do spike de VM.'
  exit 2
elif (( WARN > 0 )); then
  printf '%s\n' 'RESULTADO=PARTIAL — existe caminho para continuar; resolva ou aceite os avisos documentadamente.'
  exit 0
else
  printf '%s\n' 'RESULTADO=READY — requisitos detectados; isso não prova que uma imagem inicialize.'
  exit 0
fi
