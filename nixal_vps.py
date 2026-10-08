#!/usr/bin/env python3
"""NYXOS — controle local de VPS via libvirt/KVM.

A camada conversa somente com o hypervisor local. Não abre portas de rede,
não aceita comandos shell arbitrários e usa subprocesso com argumentos
separados. A operação de alteração continua explícita na API.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any


class VpsNyxOS:
    FONTE = "vps_nyxos"
    VERSAO = "1.0.0"
    URI = os.environ.get("NYXOS_VPS_LIBVIRT_URI", "qemu:///system")
    STORAGE = Path(
        os.environ.get(
            "NYXOS_VPS_STORAGE",
            str(Path.home() / "NyxOS" / "VPS"),
        )
    )
    NAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]{0,62}$")

    def _tool(self, name: str) -> str | None:
        return shutil.which(name)

    def _run(
        self,
        *args: str,
        timeout: float = 20.0,
    ) -> subprocess.CompletedProcess[str]:
        virsh = self._tool("virsh")
        if not virsh:
            raise RuntimeError("virsh_nao_instalado")
        return subprocess.run(
            [virsh, "-c", self.URI, *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )

    def _require_ok(self, result: subprocess.CompletedProcess[str]) -> str:
        if result.returncode != 0:
            detalhe = (result.stderr or result.stdout).strip()
            raise RuntimeError(detalhe or f"virsh_exit_{result.returncode}")
        return result.stdout.strip()

    def _nome_valido(self, nome: str) -> str:
        if not isinstance(nome, str) or not self.NAME_RE.fullmatch(nome):
            raise ValueError("nome_vps_invalido")
        return nome

    def _virsh_available(self) -> bool:
        return self._tool("virsh") is not None

    def status(self) -> dict[str, Any]:
        if not self._virsh_available():
            return {
                "sucesso": False,
                "estado": "indisponivel",
                "origem": self.FONTE,
                "versao": self.VERSAO,
                "backend": "libvirt_kvm",
                "motivo": "virsh_nao_instalado",
                "operacional": False,
            }

        try:
            version = self._require_ok(self._run("version", timeout=10))
            nodeinfo = self._require_ok(self._run("nodeinfo", timeout=10))
            domains = self._list_raw()
            return {
                "sucesso": True,
                "estado": "operacional",
                "origem": self.FONTE,
                "versao": self.VERSAO,
                "backend": "libvirt_kvm",
                "uri": self.URI,
                "operacional": True,
                "dominios": len(domains),
                "storage": str(self.STORAGE),
                "virsh": version.splitlines()[0] if version else "libvirt",
                "host": self._parse_nodeinfo(nodeinfo),
            }
        except Exception as erro:
            return {
                "sucesso": False,
                "estado": "erro_hypervisor",
                "origem": self.FONTE,
                "versao": self.VERSAO,
                "backend": "libvirt_kvm",
                "uri": self.URI,
                "operacional": False,
                "motivo": str(erro),
            }

    def _list_raw(self) -> list[str]:
        saida = self._require_ok(self._run("list", "--all", "--name"))
        return [linha.strip() for linha in saida.splitlines() if linha.strip()]

    @staticmethod
    def _parse_nodeinfo(texto: str) -> dict[str, Any]:
        dados: dict[str, Any] = {}
        for linha in texto.splitlines():
            if ":" not in linha:
                continue
            chave, valor = linha.split(":", 1)
            chave = chave.strip().lower().replace(" ", "_")
            valor = valor.strip()
            if valor.isdigit():
                dados[chave] = int(valor)
            else:
                dados[chave] = valor
        return dados

    def _ip_addresses(self, nome: str) -> list[str]:
        try:
            texto = self._require_ok(
                self._run("domifaddr", nome, "--source", "lease", timeout=10)
            )
        except Exception:
            return []

        ips: list[str] = []
        for linha in texto.splitlines():
            match = re.search(r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}(?:/\d{1,2})?\b", linha)
            if match:
                ip = match.group(0)
                if ip not in ips:
                    ips.append(ip)
        return ips

    def instances(self) -> dict[str, Any]:
        if not self._virsh_available():
            return {
                "sucesso": False,
                "estado": "indisponivel",
                "instancias": [],
                "motivo": "virsh_nao_instalado",
            }

        try:
            result: list[dict[str, Any]] = []
            for nome in self._list_raw():
                estado = self._require_ok(self._run("domstate", nome, timeout=10))
                info = self._require_ok(self._run("dominfo", nome, timeout=10))
                result.append(
                    {
                        "nome": nome,
                        "estado": estado.splitlines()[0] if estado else "desconhecido",
                        "ips": self._ip_addresses(nome),
                        "info": self._parse_dominfo(info),
                    }
                )
            return {
                "sucesso": True,
                "estado": "instancias_disponiveis",
                "origem": self.FONTE,
                "instancias": result,
            }
        except Exception as erro:
            return {
                "sucesso": False,
                "estado": "erro_listagem",
                "instancias": [],
                "motivo": str(erro),
            }

    @staticmethod
    def _parse_dominfo(texto: str) -> dict[str, Any]:
        dados: dict[str, Any] = {}
        for linha in texto.splitlines():
            if ":" not in linha:
                continue
            chave, valor = linha.split(":", 1)
            dados[chave.strip().lower().replace(" ", "_")] = valor.strip()
        return dados

    def action(self, nome: str, acao: str) -> dict[str, Any]:
        nome = self._nome_valido(nome)
        if acao not in {"start", "shutdown", "reboot", "destroy", "autostart", "autostart_off"}:
            raise ValueError("acao_vps_nao_permitida")

        comando = {
            "start": ("start", nome),
            "shutdown": ("shutdown", nome),
            "reboot": ("reboot", nome),
            "destroy": ("destroy", nome),
            "autostart": ("autostart", nome),
            "autostart_off": ("autostart", "--disable", nome),
        }[acao]

        try:
            saida = self._require_ok(self._run(*comando, timeout=60))
            return {
                "sucesso": True,
                "estado": "acao_executada",
                "origem": self.FONTE,
                "acao": acao,
                "nome": nome,
                "saida": saida,
            }
        except Exception as erro:
            return {
                "sucesso": False,
                "estado": "acao_falhou",
                "origem": self.FONTE,
                "acao": acao,
                "nome": nome,
                "motivo": str(erro),
            }

    def _criar_cloud_init(self, *, nome: str, username: str, ssh_public_key: str) -> Path:
        cloud_localds = self._tool("cloud-localds")
        if not cloud_localds:
            raise RuntimeError("cloud_localds_nao_instalado")

        seed = (self.STORAGE / f"{nome}-seed.img").resolve()
        user_data = (
            "#cloud-config\n"
            "users:\n"
            f"  - name: {username}\n"
            "    sudo: ALL=(ALL) NOPASSWD:ALL\n"
            "    groups: [adm, sudo]\n"
            "    shell: /bin/bash\n"
            "    ssh_authorized_keys:\n"
            f"      - {ssh_public_key.strip()}\n"
            "ssh_pwauth: false\n"
            "disable_root: true\n"
            "package_update: true\n"
            "packages:\n"
            "  - qemu-guest-agent\n"
            "runcmd:\n"
            "  - systemctl enable --now qemu-guest-agent || true\n"
        )
        metadata = (
            "instance-id: " + nome + "\n"
            "local-hostname: " + nome + "\n"
        )
        user_data_path = self.STORAGE / f"{nome}-user-data.yaml"
        metadata_path = self.STORAGE / f"{nome}-meta-data.yaml"
        user_data_path.write_text(user_data, encoding="utf-8")
        metadata_path.write_text(metadata, encoding="utf-8")

        try:
            result = subprocess.run(
                [
                    cloud_localds,
                    str(seed),
                    str(user_data_path),
                    str(metadata_path),
                ],
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
            if result.returncode != 0:
                raise RuntimeError((result.stderr or result.stdout).strip() or "falha_cloud_localds")
        finally:
            user_data_path.unlink(missing_ok=True)
            metadata_path.unlink(missing_ok=True)

        return seed

    def provisionar(
        self,
        *,
        nome: str,
        image_path: str,
        memory_mb: int = 2048,
        vcpus: int = 2,
        disk_gb: int = 20,
        autostart: bool = True,
        username: str = "ubuntu",
        ssh_public_key: str | None = None,
    ) -> dict[str, Any]:
        nome = self._nome_valido(nome)
        if not isinstance(image_path, str) or not image_path:
            raise ValueError("image_path_obrigatorio")
        if not 512 <= int(memory_mb) <= 262144:
            raise ValueError("memoria_vps_invalida")
        if not 1 <= int(vcpus) <= 64:
            raise ValueError("vcpus_vps_invalido")
        if not 8 <= int(disk_gb) <= 4096:
            raise ValueError("disco_vps_invalido")
        if not isinstance(username, str) or not re.fullmatch(r"[a-z_][a-z0-9_-]{0,31}", username):
            raise ValueError("usuario_vps_invalido")
        if not isinstance(ssh_public_key, str) or not ssh_public_key.strip():
            raise ValueError("ssh_public_key_obrigatoria")

        source = Path(image_path).expanduser().resolve()
        if not source.is_file():
            raise FileNotFoundError("imagem_vps_nao_encontrada")

        if not self._tool("virt-install"):
            raise RuntimeError("virt_install_nao_instalado")
        if not self._tool("qemu-img"):
            raise RuntimeError("qemu_img_nao_instalado")

        self.STORAGE.mkdir(parents=True, exist_ok=True)
        disk = (self.STORAGE / f"{nome}.qcow2").resolve()
        seed = (self.STORAGE / f"{nome}-seed.img").resolve()
        if disk.exists() or seed.exists():
            raise FileExistsError("disco_vps_ja_existe")

        seed = self._criar_cloud_init(
            nome=nome,
            username=username,
            ssh_public_key=ssh_public_key,
        )

        convert = subprocess.run(
            [
                self._tool("qemu-img"),
                "convert",
                "-p",
                "-O",
                "qcow2",
                str(source),
                str(disk),
            ],
            capture_output=True,
            text=True,
            timeout=1800,
            check=False,
        )
        if convert.returncode != 0:
            disk.unlink(missing_ok=True)
            seed.unlink(missing_ok=True)
            raise RuntimeError((convert.stderr or convert.stdout).strip() or "falha_qemu_img")

        resize = subprocess.run(
            [
                self._tool("qemu-img"),
                "resize",
                str(disk),
                f"{int(disk_gb)}G",
            ],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        if resize.returncode != 0:
            disk.unlink(missing_ok=True)
            seed.unlink(missing_ok=True)
            raise RuntimeError((resize.stderr or resize.stdout).strip() or "falha_resize")

        command = [
            self._tool("virt-install"),
            "--connect",
            self.URI,
            "--name",
            nome,
            "--memory",
            str(int(memory_mb)),
            "--vcpus",
            str(int(vcpus)),
            "--disk",
            f"path={disk},format=qcow2,bus=virtio",
            "--disk",
            f"path={seed},device=cdrom",
            "--import",
            "--network",
            "network=default,model=virtio",
            "--graphics",
            "none",
            "--noautoconsole",
            "--osinfo",
            "generic",
        ]
        created = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
        if created.returncode != 0:
            disk.unlink(missing_ok=True)
            seed.unlink(missing_ok=True)
            raise RuntimeError((created.stderr or created.stdout).strip() or "falha_virt_install")

        if autostart:
            self.action(nome, "autostart")

        return {
            "sucesso": True,
            "estado": "vps_criada",
            "origem": self.FONTE,
            "nome": nome,
            "memory_mb": int(memory_mb),
            "vcpus": int(vcpus),
            "disk_gb": int(disk_gb),
            "disk": str(disk),
            "autostart": bool(autostart),
            "username": username,
            "ssh_seed": str(seed),
        }

    def contexto(self) -> dict[str, Any]:
        return {
            "sucesso": True,
            "origem": self.FONTE,
            "versao": self.VERSAO,
            "backend": "libvirt_kvm",
            "uri": self.URI,
            "storage": str(self.STORAGE),
            "acoes": [
                "start",
                "shutdown",
                "reboot",
                "destroy",
                "autostart",
                "autostart_off",
            ],
        }


__all__ = ["VpsNyxOS"]
