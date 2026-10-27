#!/usr/bin/env python3
"""Create the disposable DELTA MVP-0 bootstrap VM using NyxOS's existing KVM layer.

This is an explicit, interactive operation. It does not install host packages, modify
host services, enable VM autostart, or touch repository-local operational JSON/log files.
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Sequence

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_IMAGE_NAME = "ubuntu-24.04-server-cloudimg-amd64.img"
DEFAULT_VM_NAME = "delta-mvp0"
MIN_FREE_BYTES = 10 * 1024**3
GIB = 1024**3
NAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]{0,62}$")


def run(command: Sequence[str], timeout: int = 20) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command),
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def require_tool(name: str) -> None:
    if shutil.which(name) is None:
        raise RuntimeError(f"ferramenta_obrigatoria_ausente:{name}")


def find_ssh_key(explicit: str | None) -> Path:
    ssh_dir = Path.home() / ".ssh"
    if explicit:
        candidates = [Path(explicit).expanduser()]
    else:
        candidates = [
            ssh_dir / "id_ed25519.pub",
            ssh_dir / "id_ecdsa.pub",
            ssh_dir / "id_rsa.pub",
        ]
        candidates.extend(sorted(p for p in ssh_dir.glob("*.pub") if p not in candidates))

    key_path = next((p.resolve() for p in candidates if p.is_file()), None)
    if key_path is None:
        raise RuntimeError(
            "chave_publica_ssh_ausente: informe --ssh-key-file com uma chave .pub existente; "
            "nenhuma chave foi criada automaticamente"
        )

    try:
        lines = [line.strip() for line in key_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    except (OSError, UnicodeDecodeError) as exc:
        raise RuntimeError("nao_foi_possivel_ler_chave_publica_ssh") from exc

    if len(lines) != 1:
        raise RuntimeError("arquivo_de_chave_deve_conter_exatamente_uma_chave_publica")
    if any(ch in lines[0] for ch in ("\r", "\n", "\x00")):
        raise RuntimeError("formato_de_chave_publica_invalido")

    require_tool("ssh-keygen")
    checked = run(["ssh-keygen", "-l", "-f", str(key_path)])
    if checked.returncode != 0:
        raise RuntimeError("ssh_keygen_rejeitou_a_chave_publica_informada")
    return key_path


def verify_image(image: Path) -> str:
    if not image.is_file():
        raise RuntimeError(
            f"imagem_base_ausente:{image}; execute antes bash deploy/vps/preparar_base_ubuntu.sh"
        )
    if image.stat().st_size > 3 * GIB:
        raise RuntimeError("imagem_base_maior_que_o_limite_esperado_de_3_GiB")

    sidecar = Path(str(image) + ".sha256")
    if not sidecar.is_file():
        raise RuntimeError(
            f"checksum_lateral_ausente:{sidecar}; prepare a imagem com "
            "deploy/vps/preparar_base_ubuntu.sh, que verifica SHA-256 antes de aceitar o arquivo"
        )
    fields = sidecar.read_text(encoding="utf-8").split()
    if len(fields) < 2 or not re.fullmatch(r"[0-9a-fA-F]{64}", fields[0]):
        raise RuntimeError("arquivo_de_checksum_invalido")
    if fields[1].lstrip("*") != image.name:
        raise RuntimeError("checksum_nao_corresponde_ao_nome_da_imagem")

    require_tool("sha256sum")
    checked = run(["sha256sum", str(image)])
    if checked.returncode != 0 or not checked.stdout:
        raise RuntimeError("falha_ao_calcular_SHA256_da_imagem")
    actual = checked.stdout.split()[0].lower()
    expected = fields[0].lower()
    if actual != expected:
        raise RuntimeError("SHA256_da_imagem_nao_confere; a VM nao sera criada")
    return actual


def check_libvirt(name: str) -> None:
    for tool in ("virsh", "virt-install", "qemu-img", "cloud-localds", "ssh-keygen"):
        require_tool(tool)

    connection = run(["virsh", "-c", "qemu:///system", "list", "--all"])
    if connection.returncode != 0:
        raise RuntimeError("libvirt_qemu_system_indisponivel_ou_sem_permissao")

    network = run(["virsh", "-c", "qemu:///system", "net-info", "default"])
    if network.returncode != 0:
        raise RuntimeError(
            "rede_libvirt_default_ausente; o script nao cria nem ativa redes automaticamente"
        )
    if not re.search(r"^Active:\s+yes\s*$", network.stdout, flags=re.MULTILINE):
        raise RuntimeError(
            "rede_libvirt_default_nao_ativa; ative/configure-a manualmente antes de provisionar"
        )

    existing = run(["virsh", "-c", "qemu:///system", "dominfo", name])
    if existing.returncode == 0:
        raise RuntimeError(f"dominio_ja_existe:{name}; nada foi alterado")


def free_space(path: Path) -> tuple[int, Path]:
    probe = path
    while not probe.exists() and probe != probe.parent:
        probe = probe.parent
    usage = shutil.disk_usage(probe)
    return usage.free, probe


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Pré-valida e cria a VM descartável inicial do DELTA usando o provisionador KVM existente."
    )
    parser.add_argument("--name", default=DEFAULT_VM_NAME, help="nome novo da VM (padrão: delta-mvp0)")
    parser.add_argument("--image", default=None, help="imagem cloud Ubuntu verificada; padrão: ~/NyxOS/VPS/ubuntu-24.04-server-cloudimg-amd64.img")
    parser.add_argument("--storage", default=None, help="diretório de discos; padrão: ~/NyxOS/VPS")
    parser.add_argument("--ssh-key-file", default=None, help="caminho para uma chave pública .pub existente")
    parser.add_argument("--memory-mb", type=int, default=2048, help="RAM da VM em MiB (padrão: 2048)")
    parser.add_argument("--vcpus", type=int, default=2, help="vCPUs da VM (padrão: 2)")
    parser.add_argument("--disk-gb", type=int, default=16, help="tamanho virtual do disco QCOW2 em GiB (padrão: 16)")
    parser.add_argument("--autostart", action="store_true", help="iniciar a VM automaticamente em boots futuros do host (desativado por padrão)")
    args = parser.parse_args()

    if not NAME_RE.fullmatch(args.name):
        print("ERRO: nome de VM inválido.", file=sys.stderr)
        return 2
    if not (1024 <= args.memory_mb <= 4096):
        print("ERRO: para este MVP, use entre 1024 e 4096 MiB de RAM.", file=sys.stderr)
        return 2
    if not (1 <= args.vcpus <= 4):
        print("ERRO: para este MVP, use entre 1 e 4 vCPUs.", file=sys.stderr)
        return 2
    if not (8 <= args.disk_gb <= 24):
        print("ERRO: para proteger o espaço do host, o disco virtual do MVP deve ficar entre 8 e 24 GiB.", file=sys.stderr)
        return 2

    configured_uri = os.environ.get("NYXOS_VPS_LIBVIRT_URI", "qemu:///system")
    if configured_uri != "qemu:///system":
        print(
            "ERRO: este helper MVP-0 valida e usa apenas qemu:///system; "
            "a variável NYXOS_VPS_LIBVIRT_URI aponta para outra URI.",
            file=sys.stderr,
        )
        return 2

    default_storage = os.environ.get(
        "NYXOS_DELTA_VM_STORAGE",
        os.environ.get("NYXOS_VPS_STORAGE", str(Path.home() / "NyxOS" / "VPS")),
    )
    default_image = os.environ.get(
        "NYXOS_VPS_BASE_IMAGE",
        str(Path.home() / "NyxOS" / "VPS" / DEFAULT_IMAGE_NAME),
    )
    storage = Path(args.storage or default_storage).expanduser().resolve()
    image = Path(args.image).expanduser().resolve() if args.image else Path(default_image).expanduser().resolve()
    os.environ["NYXOS_VPS_STORAGE"] = str(storage)

    try:
        require_tool("virsh")
        require_tool("virt-install")
        require_tool("qemu-img")
        require_tool("cloud-localds")
        key_path = find_ssh_key(args.ssh_key_file)
        image_hash = verify_image(image)
        check_libvirt(args.name)

        available, measured_path = free_space(storage)
        if available < MIN_FREE_BYTES:
            raise RuntimeError(
                f"espaco_livre_insuficiente:{available / GIB:.1f} GiB em {measured_path}; "
                f"mínimo seguro para este protótipo: {MIN_FREE_BYTES / GIB:.0f} GiB"
            )

        print("DELTA / NyxOS — plano de criação da VM MVP-0")
        print("================================================")
        print(f"VM: {args.name}")
        print("Base: Ubuntu Server 24.04 Cloud image (somente base temporária de laboratório)")
        print(f"Imagem verificada: {image}")
        print(f"SHA-256: {image_hash}")
        print(f"Armazenamento: {storage}")
        print(f"Espaço livre medido em {measured_path}: {available / GIB:.1f} GiB")
        print(f"Recursos: {args.vcpus} vCPU | {args.memory_mb} MiB RAM | {args.disk_gb} GiB virtuais QCOW2")
        print("Rede: libvirt 'default'; sem bridge público")
        print(f"Chave pública SSH: {key_path} (conteúdo não exibido)")
        print(f"Autostart futuro do host: {'habilitado' if args.autostart else 'desabilitado'}")
        print()
        print("A ação criará e iniciará uma VM, consumindo espaço em " + str(storage) + ".")
        print("Não instala pacotes no host e não importa JSONs/logs locais do checkout.")
        if not sys.stdin.isatty():
            print("ERRO: confirmação interativa necessária; execute em um terminal.", file=sys.stderr)
            return 2
        answer = input("Prosseguir com a criação da VM? Digite 's' para confirmar [s/N]: ").strip().lower()
        if answer not in {"s", "sim"}:
            print("Cancelado pelo usuário; nenhuma VM foi criada.")
            return 0

        # Import after the explicit storage setting so VpsNyxOS uses the selected path.
        sys.path.insert(0, str(ROOT))
        from nixal_vps import VpsNyxOS  # pylint: disable=import-outside-toplevel

        key_fields = key_path.read_text(encoding="utf-8").split()
        # Pass only the key type and encoded key to cloud-init; omit the free-form comment.
        public_key_for_cloud_init = " ".join(key_fields[:2])
        result = VpsNyxOS().provisionar(
            nome=args.name,
            image_path=str(image),
            memory_mb=args.memory_mb,
            vcpus=args.vcpus,
            disk_gb=args.disk_gb,
            autostart=args.autostart,
            username="ubuntu",
            ssh_public_key=public_key_for_cloud_init,
        )
        if not result.get("sucesso"):
            print("ERRO: o provisionador não confirmou sucesso.", file=sys.stderr)
            print(result, file=sys.stderr)
            return 1

        print()
        print("VM criada. A imagem é apenas a base de laboratório; o NyxOS/DELTA ainda será integrado e validado.")
        print("Próximos comandos de observação:")
        print(f"  virsh -c qemu:///system list --all")
        print(f"  virsh -c qemu:///system domifaddr {args.name} --source lease")
        print(f"  virsh -c qemu:///system console {args.name}")
        print("Não execute 'destroy' ou remova arquivos QCOW2 sem conferir o nome e o estado da VM.")
        return 0
    except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired) as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        print("Nenhuma ação de criação será tentada após uma falha de pré-validação.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
