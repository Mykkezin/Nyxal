#!/usr/bin/env bash
# Prepare a dedicated, libvirt-accessible storage directory for DELTA MVP-0.
# Changes only a new subdirectory inside an existing active directory storage pool.
set -euo pipefail

POOL="${NYXOS_DELTA_VM_POOL:-default}"
VM_NAME="${NYXOS_DELTA_VM_NAME:-delta-mvp0}"
BASE_IMAGE="${NYXOS_VPS_BASE_IMAGE:-${HOME}/NyxOS/VPS/ubuntu-24.04-server-cloudimg-amd64.img}"
BASE_HASH="${BASE_IMAGE}.sha256"

fail() { printf 'ERRO: %s\n' "$1" >&2; exit 2; }
need() { command -v "$1" >/dev/null 2>&1 || fail "ferramenta obrigatória ausente: $1"; }

need virsh
need python3
need df
need getent
need sudo
need setfacl
need getfacl

if ! getent passwd libvirt-qemu >/dev/null; then
    fail "a conta de serviço libvirt-qemu não existe neste host; não vou presumir o usuário do hipervisor"
fi
if [[ ! -f "${BASE_IMAGE}" || ! -f "${BASE_HASH}" ]]; then
    fail "imagem base ou checksum lateral ausente: ${BASE_IMAGE}; prepare e verifique a imagem primeiro"
fi
if ! sha256sum -c "${BASE_HASH}" >/dev/null 2>&1; then
    fail "o checksum local da imagem não confere; não vou preparar o armazenamento"
fi

# Never alter an existing VM/domain. The previous virt-install attempt may have
# left a definition behind, so inspect it before another provisioning attempt.
if virsh -c qemu:///system dominfo "${VM_NAME}" >/dev/null 2>&1; then
    printf 'BLOQUEADO: já existe um domínio chamado %s.\n' "${VM_NAME}" >&2
    printf 'Inspecione primeiro com:\n  virsh -c qemu:///system dominfo %s\n  virsh -c qemu:///system domblklist %s --details\n' "${VM_NAME}" "${VM_NAME}" >&2
    printf 'Este script não desregistra nem exclui domínios ou discos.\n' >&2
    exit 2
fi

POOL_INFO="$(virsh -c qemu:///system pool-info "${POOL}" 2>/dev/null || true)"
[[ -n "${POOL_INFO}" ]] || fail "pool libvirt '${POOL}' não existe ou não pode ser consultado"
if ! printf '%s\n' "${POOL_INFO}" | grep -Eq '^State:[[:space:]]+running[[:space:]]*$'; then
    fail "pool libvirt '${POOL}' não está ativo; não vou iniciar ou reconfigurar pools automaticamente"
fi

POOL_XML="$(virsh -c qemu:///system pool-dumpxml "${POOL}")"
POOL_TYPE="$(printf '%s' "${POOL_XML}" | python3 -c 'import sys,xml.etree.ElementTree as E; print(E.fromstring(sys.stdin.read()).attrib.get("type",""))')"
POOL_PATH="$(printf '%s' "${POOL_XML}" | python3 -c 'import sys,xml.etree.ElementTree as E; r=E.fromstring(sys.stdin.read()); print((r.findtext("./target/path") or "").strip())')"
[[ "${POOL_TYPE}" == "dir" ]] || fail "pool '${POOL}' tem tipo '${POOL_TYPE}', não 'dir'; este helper não altera pools de outros tipos"
[[ -n "${POOL_PATH}" && -d "${POOL_PATH}" ]] || fail "caminho do pool não existe ou não é um diretório: ${POOL_PATH}"

TARGET="${POOL_PATH%/}/delta-mvp0-storage"
if [[ -e "${TARGET}" || -L "${TARGET}" ]]; then
    fail "o destino já existe; nada será sobrescrito: ${TARGET}. Inspecione-o manualmente antes de continuar"
fi

FREE_KIB="$(df -Pk "${POOL_PATH}" | awk 'NR==2 {print $4}')"
[[ "${FREE_KIB:-}" =~ ^[0-9]+$ ]] || fail "não consegui medir o espaço livre em ${POOL_PATH}"
FREE_GIB=$((FREE_KIB / 1024 / 1024))
(( FREE_KIB >= 10 * 1024 * 1024 )) || fail "menos de 10 GiB livres no pool: ${FREE_GIB} GiB disponíveis em ${POOL_PATH}"

printf '%s\n' 'DELTA / NyxOS — armazenamento dedicado para MVP-0'
printf '%s\n' '=================================================='
printf 'Pool ativo: %s (tipo dir)\n' "${POOL}"
printf 'Diretório do pool: %s\n' "${POOL_PATH}"
printf 'Novo diretório isolado: %s\n' "${TARGET}"
printf 'Espaço livre: %s GiB\n' "${FREE_GIB}"
printf 'Imagem base (permanece em home, somente leitura pelo provisionador): %s\n' "${BASE_IMAGE}"
printf 'Acesso de QEMU será concedido somente no novo diretório; nenhuma ACL será adicionada a %s.\n' "${HOME}"
printf 'Não serão instalados pacotes, alterados serviços ou removidos arquivos.\n'
printf '\n'
printf 'A ação criará um único diretório no pool existente e aplicará ACL para a conta libvirt-qemu.\n'
read -r -p "Prosseguir? Digite 's' para confirmar [s/N]: " ANSWER
[[ "${ANSWER}" == "s" || "${ANSWER}" == "S" || "${ANSWER}" == "sim" || "${ANSWER}" == "SIM" ]] || {
    printf '%s\n' 'Cancelado; nenhuma alteração foi feita.'
    exit 0
}

sudo install -d -o "$(id -un)" -g libvirt-qemu -m 2770 -- "${TARGET}"
if ! sudo setfacl -m 'u:libvirt-qemu:rwx,d:u:libvirt-qemu:rwx' -- "${TARGET}"; then
    printf 'ERRO: ACL não aplicada. O diretório dedicado foi mantido para inspeção: %s\n' "${TARGET}" >&2
    exit 2
fi

printf '\nArmazenamento preparado. ACL resultante:\n'
getfacl -cp "${TARGET}"
printf '\nPróximo comando (a criação da VM terá outra confirmação):\n'
printf 'python3 deploy/delta/criar_vm_mvp0.py --storage %q --image %q\n' "${TARGET}" "${BASE_IMAGE}"
