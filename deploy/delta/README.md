# DELTA — ferramentas do protótipo

Este diretório abriga ferramentas pequenas e reversíveis do MVP-0. A primeira VM usa temporariamente a imagem cloud do Ubuntu Server para validar KVM, boot e acesso controlado; **isso não escolhe a distribuição final do DELTA nem significa que uma imagem NyxOS própria já exista**.

## 1. Pré-voo do host

Execute a partir de qualquer diretório no checkout:

```bash
bash deploy/delta/preflight_vm.sh
```

O pré-voo é somente de leitura. Ele verifica os arquivos-base esperados, QEMU/qemu-img, KVM, RAM, espaço, ferramentas de cloud-init e conexão/rede do libvirt. Requisitos faltantes para criar a VM são marcados como `BLOCK` e fazem o script sair com código 2; ausência de Nix/Podman ou aviso de espaço sob o recomendado fica como `WARN`. Não instala pacotes, inicia redes, altera serviços, baixa imagens ou cria VMs.

## 2. Validar os scripts

Estes comandos só verificam sintaxe; não escrevem bytecode nem alteram serviços:

```bash
bash -n deploy/delta/preflight_vm.sh
bash -n deploy/delta/diagnosticar_vm_mvp0.sh
bash -n deploy/delta/preparar_storage_mvp0.sh
bash -n deploy/vps/preparar_base_ubuntu.sh
python3 - <<'PY'
from pathlib import Path
path = Path("deploy/delta/criar_vm_mvp0.py")
compile(path.read_text(encoding="utf-8"), str(path), "exec")
print("PYTHON_SYNTAX_OK")
PY
```

A suíte mockada do helper de VM pode ser executada sem criar ou alterar uma VM real:

```bash
python3 -m unittest discover -s deploy/delta -p 'teste_*.py' -v
```

O workflow de DELTA compila e executa essa suíte junto das regressões de bootstrap e VPS.

## 3. Preparar a imagem de laboratório

```bash
bash deploy/vps/preparar_base_ubuntu.sh
```

O script baixa a lista `SHA256SUMS` do diretório oficial da imagem Ubuntu 24.04 e compara o SHA-256 da imagem antes de aceitá-la. Uma imagem existente não é sobrescrita quando o hash não corresponde ao release atualmente publicado. O script deixa um sidecar `.sha256` para a verificação local posterior.

A lista de checksums e a imagem vêm do mesmo endpoint HTTPS; essa verificação protege contra arquivo incompleto/corrompido, mas não equivale, sozinha, a verificar criptograficamente a assinatura GPG da lista. Fonte oficial sobre checksums e verificação de imagens: https://ubuntu.com/docs/public-images/public-images-how-to/verify-image-checksum/.

Armazenamento padrão:

```text
~/NyxOS/VPS/ubuntu-24.04-server-cloudimg-amd64.img
~/NyxOS/VPS/ubuntu-24.04-server-cloudimg-amd64.img.sha256
```

A imagem cloud atual tem aproximadamente 600 MB; o tamanho e o hash podem mudar conforme a Canonical publique outro release. Mantenha espaço para o disco da VM e dados instalados, não apenas para o download.

## 4. Recuperar a tentativa anterior e preparar armazenamento acessível

A primeira tentativa mostrou que `libvirt-qemu` não consegue pesquisar `/home/nyxal`. Não use `chmod 777` e não altere permissões da home inteira. O pool existente `VPS` também aponta para dentro da home, por isso **não deve ser usado para os discos da VM**.

Primeiro execute o diagnóstico, que é somente de leitura:

```bash
bash deploy/delta/diagnosticar_vm_mvp0.sh
```

O diagnóstico também emite `GUEST_AGENT_CHANNEL` e `GUEST_AGENT_PING`:
- `GUEST_AGENT_CHANNEL=present`: o XML libvirt contém `org.qemu.guest_agent.0`.
- `GUEST_AGENT_CHANNEL=absent`: a definição da VM não declara esse canal.
- `GUEST_AGENT_CHANNEL=unknown`: não foi possível ler/interpretar o XML, ou o domínio não foi confirmado.
- `GUEST_AGENT_PING=success`: o QEMU Guest Agent respondeu a um `guest-ping` somente de leitura.
- `GUEST_AGENT_PING=failed`: canal presente e VM executando, mas o agente não respondeu.
- `not_attempted` ou `not_running`: o ping não foi executado porque faltava uma pré-condição.

O ping não instala, reinicia, inicia ou para serviços. Se falhar, use o console da VM para inspecionar manualmente (sem alterar estado):

```bash
systemctl is-active qemu-guest-agent
dpkg-query -W -f='${Status} ${Version}\n' qemu-guest-agent
test -e /dev/virtio-ports/org.qemu.guest_agent.0 && echo GUEST_AGENT_DEVICE_PRESENT
```

Não reinicie o agente automaticamente a partir do host. Primeiro diferencie ausência do canal no XML, dispositivo virtio ausente dentro da VM e serviço instalado mas inativo.

Se ele indicar `DOMAIN_EXISTS=yes`, **não crie outra VM ainda**. Inspecione o estado e os caminhos com os comandos exibidos; não desregistre um domínio até confirmar que é a tentativa descartável e não uma VM anterior do usuário. O diagnóstico não remove nem altera nada.

Se indicar `DOMAIN_EXISTS=unknown`, a conexão/listagem do libvirt não permitiu determinar o estado. **Não crie outra VM nem remova discos**; corrija a conexão/permissões e repita o diagnóstico. O script só informa `DOMAIN_EXISTS=no` depois de uma listagem bem-sucedida confirmar que o nome não existe.

O diagnóstico examina os artefatos na pasta configurada (`NYXOS_DELTA_VM_STORAGE` / `NYXOS_VPS_STORAGE`), no armazenamento dedicado padrão (`/var/lib/libvirt/images/delta-mvp0-storage`) e na pasta legada `~/NyxOS/VPS`. Isso permite encontrar sobras tanto da primeira tentativa quanto das tentativas feitas com armazenamento dedicado. O script permanece somente de leitura.

Se indicar `DOMAIN_EXISTS=no`, prepare um diretório dedicado fora da home:

```bash
bash deploy/delta/preparar_storage_mvp0.sh
```

Por padrão, o helper usa `/var/lib/libvirt/images`, o diretório de sistema padrão para imagens de VM no Ubuntu/Mint. Antes de criar qualquer coisa, ele confirma que esse diretório existe, que a conta `libvirt-qemu` consegue atravessá-lo, que há pelo menos 10 GiB livres, que o checksum da imagem confere e que não existe domínio com o nome planejado. O helper exige confirmação e cria somente `delta-mvp0-storage`, com uma ACL específica para `libvirt-qemu`. Não altera a home, não modifica o pool `VPS`, não cria/ativa pools, não instala pacotes e não remove arquivos.

Caso o armazenamento padrão não exista ou não seja acessível ao QEMU, o script interrompe sem criar a pasta. Só indique outro diretório existente fora da home por meio de `NYXOS_DELTA_STORAGE_ROOT` depois de confirmar que é um caminho apropriado para arquivos de VM.

## 5. Criar a VM descartável MVP-0

O helper de armazenamento imprime o caminho exato e o comando para a criação. Também é possível executar o comando manualmente, passando o caminho informado pelo helper e a imagem base na home:

```bash
python3 deploy/delta/criar_vm_mvp0.py \
  --storage "/CAMINHO/DO/ARMAZENAMENTO/delta-mvp0-storage" \
  --image "$HOME/NyxOS/VPS/ubuntu-24.04-server-cloudimg-amd64.img"
```

A criação requer uma chave pública SSH válida, `cloud-localds`, a rede libvirt `default` ativa e pelo menos 10 GiB livres no filesystem do armazenamento VM. Nenhuma chave será gerada pelo script. O provisionador valida o hash local, a conexão libvirt, a rede default, o domínio, a chave pública e o espaço antes de apresentar a confirmação final.

Padrões do plano, apresentados antes da confirmação:
- nome `delta-mvp0`;
- 2 vCPUs e 2048 MiB de RAM;
- disco QCOW2 de 16 GiB virtuais;
- rede NAT libvirt `default`;
- login `ubuntu` com chave pública SSH existente;
- autostart em boots futuros do host desligado, salvo quando `--autostart` for explicitamente informado.

O provisionador reutiliza `nixal_vps.py`; não implementa um segundo gerenciador de VMs. Se qualquer pré-condição falhar, aborta em vez de instalar pacotes ou reconfigurar o host automaticamente.

Se a chave pública não for a padrão, indique um caminho explícito:

```bash
python3 deploy/delta/criar_vm_mvp0.py \
  --ssh-key-file ~/.ssh/minha_chave.pub \
  --storage "/CAMINHO/DO/ARMAZENAMENTO/delta-mvp0-storage" \
  --image "$HOME/NyxOS/VPS/ubuntu-24.04-server-cloudimg-amd64.img"
```

## 6. Observar o primeiro boot

Após a confirmação e criação:

```bash
virsh -c qemu:///system list --all
virsh -c qemu:///system domifaddr delta-mvp0 --source lease
virsh -c qemu:///system console delta-mvp0
```

A VM inicial é uma base Ubuntu Server de laboratório, sem o desktop DELTA e sem instalação automática da Nyxal. O próximo passo será confirmar o boot e a conectividade, depois integrar os serviços NyxOS de modo explícito e testável.

Para sair do console serial sem desligar a VM, use a sequência de escape do console libvirt/QEMU que o terminal indicar; não use comandos de destruição da VM como substituto para desligamento normal.

## Segurança e escopo

- Nunca copie `nyxal.env`, tokens, OAuth ou os JSONs/logs operacionais do host para a VM.
- A chave privada SSH permanece no host; apenas a chave pública é entregue ao cloud-init.
- A conta de laboratório criada pelo provisionador existente tem sudo sem senha dentro da VM. Use apenas para este ambiente descartável, em rede NAT local; não reutilize credenciais ou dados sensíveis.
- O script não instala pacotes no host, não ativa redes automaticamente, não altera `main` e não lê nem importa os arquivos operacionais locais da Nyxal.
- A existência da VM não comprova o MVP: boot, acesso, serviço, persistência, atualização e recuperação precisam de evidência separada.
