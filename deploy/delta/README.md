# DELTA — ferramentas do protótipo

Este diretório abriga ferramentas pequenas e reversíveis do MVP-0. Não é ainda uma receita de imagem DELTA, e a existência destes scripts não prova que uma VM esteja inicializando.

## Pré-voo do host

Execute a partir de qualquer diretório no checkout do repositório:

```bash
bash deploy/delta/preflight_vm.sh
```

O pré-voo é somente de leitura. Ele verifica arquivos-base esperados no checkout, presença de QEMU/qemu-img, disponibilidade de `/dev/kvm`, memória, espaço livre e presença opcional de ferramentas de virtualização/empacotamento.

O script **não**:
- instala ou atualiza pacotes;
- inicia, para ou habilita serviços;
- altera grupos ou permissões;
- baixa imagens;
- cria, inicia ou remove VMs;
- escreve no repositório, configurações locais ou dados da Nyxal.

## Interpretação

- `RESULTADO=READY`: requisitos detectados; ainda é necessário construir e inicializar uma imagem para provar o MVP.
- `RESULTADO=PARTIAL`: existem avisos. Resolver ou aceitar cada aviso com justificativa antes do experimento.
- `RESULTADO=BLOCKED`: falta requisito essencial ou algum arquivo do checkout esperado.

O pré-voo não escolhe a distribuição. NixOS e Fedora bootc serão comparados com critérios idênticos conforme `docs/DELTA_MVP_ACCEPTANCE.md`. Não classificar uma base como aprovada apenas porque suas ferramentas estão instaladas.
