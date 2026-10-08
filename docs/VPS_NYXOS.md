# VPS NyxOS

## Objetivo

O primeiro atalho do Infinity passa a controlar o backend de VPS local do NyxOS.

A implementação usa **libvirt/KVM** como hypervisor e o comando `virsh` para gerenciamento. O libvirt permite listar, iniciar, desligar, reiniciar, destruir e configurar autostart de domínios; a camada NyxOS chama essas operações sem aceitar shell arbitrário.

## Componentes

- `nixal_vps.py` — camada de controle do hypervisor.
- `nyxal_web_api.py` — endpoints locais:
  - `GET /api/vps/status`
  - `GET /api/vps/instances`
  - `GET /api/vps/contexto`
  - `POST /api/vps/action`
  - `POST /api/vps/provisionar`
- `interface/index.html` — primeiro atalho Infinity funcional.
- `deploy/vps/instalar_nyxos_vps.sh` — instala KVM/libvirt/virt-install/qemu-img em Debian/Ubuntu.
- `deploy/vps/preparar_base_ubuntu.sh` — baixa uma imagem oficial Ubuntu Server 24.04 para servir de base.
- `teste_nixal_vps.py` — validações determinísticas da camada.

As imagens Ubuntu Cloud são publicadas oficialmente pela Canonical e incluem imagens para execução em KVM.

## Preparação no host

Depois de instalar o NyxOS:

```bash
cd ~/Nyxal
bash deploy/vps/instalar_nyxos_vps.sh
```

Faça logout/login para os grupos `libvirt` e `kvm` entrarem na sessão.

Depois:

```bash
bash deploy/vps/preparar_base_ubuntu.sh
virsh -c qemu:///system list --all
```

A imagem base fica, por padrão, em:

```text
~/NyxOS/VPS/ubuntu-24.04-server-cloudimg-amd64.img
```

## Provisionamento

No Infinity → **VPS**, informe:

- nome da VPS;
- caminho da imagem base;
- RAM;
- vCPU;
- disco.

O NyxOS cria um disco QCOW2 independente e registra a máquina no libvirt. A instância pode ser iniciada automaticamente.

## Limite atual

Esta primeira versão é o **control plane local**. Ela ainda não é um produto de hospedagem público: IP público, NAT/bridge dedicado, DNS, cobrança, isolamento comercial, snapshots, backup, migração e painel de cliente ficam para as próximas etapas.

A arquitetura foi deixada preparada para evoluir para isso sem transformar o NyxOS em um executor de shell arbitrário.
