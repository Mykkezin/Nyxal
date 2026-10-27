#!/usr/bin/env bash
# Prepare dedicated VM storage outside the user's home, with a scoped QEMU ACL.
# The base image and the repository's operational data remain untouched.
set -euo pipefail

VM_NAME="${NYXOS_DELTA_VM_NAME:-delta-mvp0}"
BASE_IMAGE="${NYXOS_VPS_BASE_IMAGE:-${HOME}/NyxOS/VPS/ubuntu-24.04-server-cloudimg-amd64.img}"
BASE_HASH="${BASE_IMAGE}.sha256"
STORAGE_ROOT="${NYXOS_DELTA_STORAGE_ROOT:-/var/lib/libvirt/images}"

fail() { printf 'ERRO: %s\n' "$1" >&2; exit 2; }
need() { command -v "$1" >/dev/null 2>&1 || fail "ferramenta obrigatória ausente: $1"; }

need virsh
need python3
need df
need getent
need sudo
need setfacl
need getfacl
need realpath

if ! getent passwd libvirt-qemu >/dev/null; then
    fail "a conta de serviço libvirt-qemu não existe neste host; não vou presumir o usuário do hipervisor"
fi
if [[ ! -f "${BASE_IMAGE}" || ! -f "${BASE_HASH}" ]]; then
    fail "imagem base ou checksum lateral ausente: ${BASE_IMAGE}; prepare e verifique a imagem primeiro"
fi
if ! (cd -- "$(dirname -- "${BASE_IMAGE}")" && sha256sum -c "$(basename -- "${BASE_HASH}")") >/dev/null 2>&1; then
    fail "o checksum local da imagem não confere; não vou preparar o armazenamento"
fi

# Never alter an existing VM/domain. A previous virt-install attempt can leave
# a definition behind, so inspect it before preparing another storage location.
if virsh -c qemu:///system dominfo "${VM_NAME}" >/dev/null 2>&1; then
    printf 'BLOQUEADO: já existe um domínio chamado %s.\n' "${VM_NAME}" >&2
    printf 'Inspecione primeiro com:\n  virsh -c qemu:///system dominfo %s\n  virsh -c qemu:///system domblklist %s --details\n' "${VM_NAME}" "${VM_NAME}" >&2
    printf 'Este script não desregistra nem exclui domínios ou discos.\n' >&2
    exit 2
fi

[[ -d "${STORAGE_ROOT}" ]] || fail "diretório de armazenamento do libvirt ausente: ${STORAGE_ROOT}; não vou criar nem reconfigurar um pool automaticamente"
STORAGE_ROOT="$(realpath -e -- "${STORAGE_ROOT}")"
HOME_REAL="$(realpath -e -- "${HOME}")"
case "${STORAGE_ROOT}" in
    "${HOME_REAL}"|"${HOME_REAL}"/*)
        fail "armazenamento dentro da home não é permitido: ${STORAGE_ROOT}; escolha um diretório de sistema acessível ao libvirt"
        ;;
esac

# Check all parent-directory traversal before creating anything.
if ! sudo -u libvirt-qemu test -x "${STORAGE_ROOT}"; then
    fail "libvirt-qemu não consegue atravessar ${STORAGE_ROOT}; nenhuma pasta foi criada. Verifique o caminho ou indique outro STORAGE_ROOT seguro"
fi

TARGET="${STORAGE_ROOT%/}/delta-mvp0-storage"
if [[ -e "${TARGET}" || -L "${TARGET}" ]]; then
    fail "o destino já existe; nada será sobrescrito: ${TARGET}. Inspecione-o manualmente antes de continuar"
fi

FREE_KIB="$(df -Pk "${STORAGE_ROOT}" | awk 'NR==2 {print $4}')"
[[ "${FREE_KIB:-}" =~ ^[0-9]+$ ]] || fail "não consegui medir o espaço livre em ${STORAGE_ROOT}"
FREE_GIB=$((FREE_KIB / 1024 / 1024))
(( FREE_KIB >= 10 * 1024 * 1024 )) || fail "menos de 10 GiB livres no armazenamento: ${FREE_GIB} GiB disponíveis em ${STORAGE_ROOT}"

printf '%s\n' 'DELTA / NyxOS — armazenamento dedicado para MVP-0'
printf '%s\n' '=================================================='
printf 'Diretório de sistema acessível ao QEMU: %s\n' "${STORAGE_ROOT}"
printf 'Novo diretório isolado: %s\n' "${TARGET}"
printf 'Espaço livre: %s GiB\n' "${FREE_GIB}"
printf 'Imagem base (permanece na home; provisionador a lê para conversão): %s\n' "${BASE_IMAGE}"
printf 'ACL será aplicada somente ao novo diretório; nenhuma ACL será adicionada à home.\n'
printf 'O pool VPS existente não será alterado nem usado para os discos da VM.\n'
printf 'Não serão instalados pacotes, alterados serviços ou removidos arquivos.\n'
printf '\n'
printf 'A ação criará um único diretório e aplicará ACL para a conta libvirt-qemu.\n'
read -r -p "Prosseguir? Digite 's' para confirmar [s/N]: " ANSWER
[[ "${ANSWER}" == "s" || "${ANSWER}" == "S" || "${ANSWER}" == "sim" || "${ANSWER}" == "SIM" ]] || {
    printf '%s\n' 'Cancelado; nenhuma alteração foi feita.'
    exit 0
}

QEMU_GROUP="$(id -gn libvirt-qemu)"
sudo install -d -o "$(id -un)" -g "${QEMU_GROUP}" -m 2770 -- "${TARGET}"
if ! sudo setfacl -m 'u:libvirt-qemu:rwx,d:u:libvirt-qemu:rwx' -- "${TARGET}"; then
    printf 'ERRO: ACL não aplicada. O diretório dedicado foi mantido para inspeção: %s\n' "${TARGET}" >&2
    exit 2
fi

printf '\nArmazenamento preparado. ACL resultante:\n'
getfacl -cp "${TARGET}"
printf '\nPróximo comando (a criação da VM terá outra confirmação):\n'
printf 'python3 deploy/delta/criar_vm_mvp0.py --storage %q --image %q\n' "${TARGET}" "${BASE_IMAGE}"
