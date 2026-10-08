#!/usr/bin/env bash
set -euo pipefail

echo "=== NyxOS VPS / KVM — instalação do backend ==="

if [[ "${EUID}" -eq 0 ]]; then
    echo "Execute este instalador como seu usuário normal; ele usa sudo quando necessário."
    exit 1
fi

if ! command -v sudo >/dev/null 2>&1; then
    echo "ERRO: sudo não encontrado."
    exit 1
fi

if ! command -v apt-get >/dev/null 2>&1; then
    echo "ERRO: este instalador está preparado para Debian/Ubuntu."
    echo "Em outra distribuição, instale manualmente: qemu-kvm, libvirt, virsh, virt-install e qemu-img."
    exit 1
fi

sudo apt-get update
sudo apt-get install -y     qemu-kvm     libvirt-daemon-system     libvirt-clients     virtinst     qemu-utils

if systemctl list-unit-files libvirtd.service >/dev/null 2>&1; then
    sudo systemctl enable --now libvirtd.service || true
fi

sudo usermod -aG libvirt "${USER}" || true
sudo usermod -aG kvm "${USER}" || true

mkdir -p "${HOME}/NyxOS/VPS"

echo
echo "Backend instalado."
echo "Storage: ${HOME}/NyxOS/VPS"
echo
echo "ATENÇÃO: sua sessão precisa ser encerrada e aberta novamente"
echo "para que os grupos libvirt/kvm sejam reconhecidos."
echo
echo "Validação depois do novo login:"
echo "  virsh -c qemu:///system list --all"
echo "  virsh -c qemu:///system nodeinfo"
