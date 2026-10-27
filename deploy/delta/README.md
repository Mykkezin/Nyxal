# DELTA — ferramentas do protótipo

Este diretório abriga ferramentas pequenas e reversíveis do MVP-0. A primeira VM usa temporariamente a imagem cloud do Ubuntu Server para validar KVM, boot e acesso controlado; **isso não escolhe a distribuição final do DELTA nem significa que uma imagem NyxOS própria já exista**.

## 1. Pré-voo do host

Execute a partir de qualquer diretório no checkout:

```bash
bash deploy/delta/preflight_vm.sh
```

O pré-voo é somente de leitura. Ele verifica os arquivos-base esperados, QEMU/qemu-img, KVM, RAM, espaço, ferramentas de cloud-init e conexão/rede do libvirt. Não instala pacotes, inicia redes, altera serviços, baixa imagens ou cria VMs.

## 2. Preparar a imagem de laboratório

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

## 3. Criar a VM descartável MVP-0

Confirme que existe uma chave pública SSH em `~/.ssh/*.pub`, que `cloud-localds` está instalado e que a rede libvirt `default` está ativa. Nenhuma chave será gerada pelo script.

```bash
python3 deploy/delta/criar_vm_mvp0.py
```

Padrões do plano, apresentados antes de uma confirmação interativa:
- nome `delta-mvp0`;
- 2 vCPUs e 2048 MiB de RAM;
- disco QCOW2 de 16 GiB virtuais, que cresce conforme os dados são escritos;
- rede NAT libvirt `default`;
- login `ubuntu` com chave pública SSH existente;
- autostart em boots futuros do host desligado, salvo quando `--autostart` for explicitamente informado.

O script verifica o hash local da imagem, a conexão `qemu:///system`, a rede `default`, o domínio, a chave SSH e pelo menos 10 GiB livres. Ele usa o provisionador existente `nixal_vps.py`; não implementa um segundo gerenciador de VMs. A criação e o primeiro boot só acontecem depois de o operador digitar `s` no prompt.

Se a chave pública não for a padrão, indique um caminho explícito:

```bash
python3 deploy/delta/criar_vm_mvp0.py --ssh-key-file ~/.ssh/minha_chave.pub
```

Se qualquer pré-condição falhar, o processo aborta em vez de instalar pacotes ou reconfigurar o host automaticamente.

## 4. Observar o primeiro boot

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
