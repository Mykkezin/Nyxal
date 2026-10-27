#!/usr/bin/env python3
"""NYXOS — controle local de VPS via libvirt/KVM.

A camada conversa somente com o hypervisor local. Não abre portas de rede,
não aceita comandos shell arbitrários e usa subprocesso com argumentos
separados. A operação de alteração continua explícita na API.
"""

from __future__ import annotations

import base64
import binascii
import json
import os
import re
import shutil
import subprocess
import tempfile
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

    @staticmethod
    def _validar_chave_ssh(chave: str) -> str:
        """Valida a estrutura OpenSSH e evita injeção de linhas no cloud-init."""
        if not isinstance(chave, str) or not chave.strip():
            raise ValueError("ssh_public_key_obrigatoria")
        valor = chave.strip()
        if len(valor) > 16384 or "\n" in valor or "\r" in valor:
            raise ValueError("ssh_public_key_invalida")

        padrao = re.fullmatch(
            r"(ssh-ed25519|ssh-rsa|ecdsa-sha2-nistp256|ecdsa-sha2-nistp384|"
            r"ecdsa-sha2-nistp521|sk-ssh-ed25519@openssh\.com|"
            r"sk-ecdsa-sha2-nistp256@openssh\.com)[ \t]+"
            r"([A-Za-z0-9+/]+={0,2})(?:[ \t]+[^\r\n]*)?",
            valor,
        )
        if not padrao:
            raise ValueError("ssh_public_key_invalida")
        tipo = padrao.group(1)
        try:
            blob = base64.b64decode(padrao.group(2), validate=True)
        except (ValueError, binascii.Error) as erro:
            raise ValueError("ssh_public_key_invalida") from erro

        def ler_campo(dados: bytes, posicao: int) -> tuple[bytes, int]:
            if posicao + 4 > len(dados):
                raise ValueError("ssh_public_key_invalida")
            tamanho = int.from_bytes(dados[posicao:posicao + 4], "big")
            inicio = posicao + 4
            fim = inicio + tamanho
            if tamanho <= 0 or fim > len(dados):
                raise ValueError("ssh_public_key_invalida")
            return dados[inicio:fim], fim

        try:
            nome_blob, posicao = ler_campo(blob, 0)
            if nome_blob.decode("ascii") != tipo:
                raise ValueError("ssh_public_key_invalida")
            if tipo in {"ssh-ed25519", "sk-ssh-ed25519@openssh.com"}:
                public_key, posicao = ler_campo(blob, posicao)
                if len(public_key) != 32:
                    raise ValueError("ssh_public_key_invalida")
                if tipo.startswith("sk-"):
                    aplicacao, posicao = ler_campo(blob, posicao)
                    if not aplicacao:
                        raise ValueError("ssh_public_key_invalida")
            elif tipo == "ssh-rsa":
                expoente, posicao = ler_campo(blob, posicao)
                modulo, posicao = ler_campo(blob, posicao)
                expoente_valor = int.from_bytes(expoente, "big", signed=False)
                modulo_valor = int.from_bytes(modulo, "big", signed=False)
                if (
                    expoente_valor < 3
                    or expoente_valor % 2 == 0
                    or modulo_valor <= expoente_valor
                    or modulo_valor % 2 == 0
                    or modulo_valor.bit_length() < 2048
                ):
                    raise ValueError("ssh_public_key_invalida")
            else:
                curva, posicao = ler_campo(blob, posicao)
                ponto, posicao = ler_campo(blob, posicao)
                tipo_ec = tipo.split("@", 1)[0]
                curva_esperada = tipo_ec.rsplit("nistp", 1)[-1]
                if curva.decode("ascii") != "nistp" + curva_esperada:
                    raise ValueError("ssh_public_key_invalida")
                parametros_curva = {
                    "256": (
                        int("FFFFFFFF00000001000000000000000000000000FFFFFFFFFFFFFFFFFFFFFFFF", 16),
                        int("5AC635D8AA3A93E7B3EBBD55769886BC651D06B0CC53B0F63BCE3C3E27D2604B", 16),
                        32,
                    ),
                    "384": (
                        int("FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFFFF0000000000000000FFFFFFFF", 16),
                        int("B3312FA7E23EE7E4988E056BE3F82D19181D9C6EFE8141120314088F5013875AC656398D8A2ED19D2A85C8EDD3EC2AEF", 16),
                        48,
                    ),
                    "521": (
                        (1 << 521) - 1,
                        int("0051953EB9618E1C9A1F929A21A0B68540EEA2DA725B99B315F3B8B489918EF109E156193951EC7E937B1652C0BD3BB1BF073573DF883D2C34F1EF451FD46B503F00", 16),
                        66,
                    ),
                }
                primo, constante_b, tamanho_coordenada = parametros_curva[curva_esperada]
                tamanho_ponto = 1 + 2 * tamanho_coordenada
                if len(ponto) != tamanho_ponto or not ponto.startswith(b"\x04"):
                    raise ValueError("ssh_public_key_invalida")
                coordenada_x = int.from_bytes(ponto[1:1 + tamanho_coordenada], "big")
                coordenada_y = int.from_bytes(ponto[1 + tamanho_coordenada:], "big")
                if (
                    coordenada_x >= primo
                    or coordenada_y >= primo
                    or (pow(coordenada_y, 2, primo) - (
                        pow(coordenada_x, 3, primo) - 3 * coordenada_x + constante_b
                    )) % primo != 0
                ):
                    raise ValueError("ssh_public_key_invalida")
                if tipo.startswith("sk-"):
                    aplicacao, posicao = ler_campo(blob, posicao)
                    if not aplicacao:
                        raise ValueError("ssh_public_key_invalida")
            if posicao != len(blob):
                raise ValueError("ssh_public_key_invalida")
        except (UnicodeDecodeError, ValueError, KeyError) as erro:
            raise ValueError("ssh_public_key_invalida") from erro

        # O comentário não é necessário para autenticação e poderia conter
        # caracteres com semântica especial no YAML; mantenha tipo e blob.
        return f"{tipo} {padrao.group(2)}"

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
        # Defense in depth: este sink nunca deve interpolar dados não validados
        # em user-data YAML, mesmo se um futuro chamador contornar provisionar().
        nome = self._nome_valido(nome)
        if not isinstance(username, str) or not re.fullmatch(r"[a-z_][a-z0-9_-]{0,31}", username):
            raise ValueError("usuario_vps_invalido")
        ssh_public_key = self._validar_chave_ssh(ssh_public_key)

        storage_configurada = Path(self.STORAGE).expanduser()
        if storage_configurada.is_symlink():
            raise RuntimeError("storage_vps_link_simbolico")
        if not storage_configurada.is_dir():
            raise RuntimeError("storage_vps_nao_preparado")
        storage = storage_configurada.resolve()
        self.STORAGE = storage

        seed = storage / f"{nome}-seed.img"
        user_data_final = storage / f"{nome}-user-data.yaml"
        metadata_final = storage / f"{nome}-meta-data.yaml"
        # Do not follow dangling symlinks or overwrite artefacts left by earlier runs.
        for caminho in (seed, user_data_final, metadata_final):
            if caminho.is_symlink() or caminho.exists():
                raise FileExistsError("artefato_cloud_init_ja_existe")

        cloud_localds = self._tool("cloud-localds")
        if not cloud_localds:
            raise RuntimeError("cloud_localds_nao_instalado")

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

        # Work in a private, unpredictable staging directory on the same filesystem.
        # The fixed final name is linked only after cloud-localds succeeds; os.link
        # fails rather than overwriting a path created concurrently by another process.
        with tempfile.TemporaryDirectory(
            prefix=f".{nome}-cloud-init-",
            dir=str(storage),
        ) as diretorio_temporario:
            temporario = Path(diretorio_temporario)
            seed_temporario = temporario / "seed.img"
            user_data_path = temporario / "user-data.yaml"
            metadata_path = temporario / "meta-data.yaml"

            with user_data_path.open("x", encoding="utf-8") as arquivo:
                arquivo.write(user_data)
            with metadata_path.open("x", encoding="utf-8") as arquivo:
                arquivo.write(metadata)

            result = subprocess.run(
                [
                    cloud_localds,
                    str(seed_temporario),
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
            if seed_temporario.is_symlink() or not seed_temporario.is_file():
                raise RuntimeError("saida_cloud_localds_invalida")

            try:
                os.link(seed_temporario, seed)
            except FileExistsError as erro:
                raise FileExistsError("seed_vps_ja_existe") from erro
            try:
                # The dedicated DELTA storage uses a service-scoped group/ACL.
                os.chmod(seed, 0o640)
            except OSError:
                try:
                    seed.unlink()
                except OSError:
                    pass
                raise
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
        ssh_public_key = self._validar_chave_ssh(ssh_public_key)

        source = Path(image_path).expanduser().resolve()
        if not source.is_file():
            raise FileNotFoundError("imagem_vps_nao_encontrada")

        if not self._tool("virt-install"):
            raise RuntimeError("virt_install_nao_instalado")
        if not self._tool("qemu-img"):
            raise RuntimeError("qemu_img_nao_instalado")

        storage_configurada = Path(self.STORAGE).expanduser()
        if storage_configurada.is_symlink():
            raise RuntimeError("storage_vps_link_simbolico")
        storage_configurada.mkdir(parents=True, exist_ok=True)
        if storage_configurada.is_symlink() or not storage_configurada.is_dir():
            raise RuntimeError("storage_vps_invalido")
        storage = storage_configurada.resolve()
        self.STORAGE = storage

        # Use unresolved child names for lstat-style symlink checks. Calling
        # resolve() on a dangling symlink would otherwise hide the link itself.
        disk = storage / f"{nome}.qcow2"
        seed = storage / f"{nome}-seed.img"
        user_data_path = storage / f"{nome}-user-data.yaml"
        metadata_path = storage / f"{nome}-meta-data.yaml"
        for caminho in (disk, seed, user_data_path, metadata_path):
            if caminho.is_symlink() or caminho.exists():
                raise FileExistsError("artefato_vps_ja_existe")

        seed = self._criar_cloud_init(
            nome=nome,
            username=username,
            ssh_public_key=ssh_public_key,
        )

        # Convert/resize the base image in a private staging directory so qemu-img
        # never writes through a pre-existing disk path. The final hard link is
        # created exclusively and stays on the storage filesystem.
        with tempfile.TemporaryDirectory(
            prefix=f".{nome}-disk-",
            dir=str(storage),
        ) as diretorio_temporario:
            disk_temporario = Path(diretorio_temporario) / f"{nome}.qcow2"
            convert = subprocess.run(
                [
                    self._tool("qemu-img"),
                    "convert",
                    "-p",
                    "-O",
                    "qcow2",
                    str(source),
                    str(disk_temporario),
                ],
                capture_output=True,
                text=True,
                timeout=1800,
                check=False,
            )
            if convert.returncode != 0:
                seed.unlink(missing_ok=True)
                raise RuntimeError((convert.stderr or convert.stdout).strip() or "falha_qemu_img")

            resize = subprocess.run(
                [
                    self._tool("qemu-img"),
                    "resize",
                    str(disk_temporario),
                    f"{int(disk_gb)}G",
                ],
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )
            if resize.returncode != 0:
                seed.unlink(missing_ok=True)
                raise RuntimeError((resize.stderr or resize.stdout).strip() or "falha_resize")

            if disk_temporario.is_symlink() or not disk_temporario.is_file():
                seed.unlink(missing_ok=True)
                raise RuntimeError("disco_temporario_invalido")
            try:
                os.link(disk_temporario, disk)
            except FileExistsError as erro:
                seed.unlink(missing_ok=True)
                raise FileExistsError("disco_vps_ja_existe") from erro
            try:
                # Preserve owner/group from the setgid storage directory but limit
                # access to its owner and service group, not every local account.
                os.chmod(disk, 0o660)
            except OSError:
                try:
                    disk.unlink()
                except OSError:
                    pass
                try:
                    seed.unlink()
                except OSError:
                    pass
                raise

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
            "--channel",
            "unix,target.type=virtio,target.name=org.qemu.guest_agent.0",
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
