# DELTA — Plano do Primeiro Protótipo e Critérios de Aceite

**Estado:** plano de execução para revisão  
**Dependência:** `docs/DELTA_PLATFORM_SPEC.md`  
**Princípio:** provar uma imagem recuperável antes de desenvolver compatibilidade adicional.

## Objetivo do MVP-0

Produzir a primeira imagem experimental inicializável do NyxOS, sob a identidade de produto DELTA, em uma máquina virtual. O protótipo deve iniciar de modo repetível, apresentar uma sessão utilizável, executar os serviços NyxOS existentes sem privilegiar o runtime Nyxal e preservar o estado do usuário entre reinicializações.

Este MVP não pretende executar todos os aplicativos Windows/macOS/Android. O objetivo imediato é provar a fundação do produto e a capacidade de instalá-lo, observá-lo, atualizar e recuperar com segurança.

## Escopo incluído

- build reproduzível de uma imagem de VM;
- seleção de base por um experimento comparativo documentado;
- boot, login, sessão gráfica e rede funcional;
- instalação versionada dos serviços NyxOS já existentes;
- API Nyxal e serviço residente com identidade/permissões mínimas;
- estado persistente separado do sistema base;
- health checks, logs e diagnóstico acessíveis;
- teste de reinicialização e procedimento de recuperação;
- documentação de limitações, dependências e ambiente usado.

## Fora do escopo do MVP-0

- kernel próprio, microkernel ou fusão NT/Linux;
- substituir drivers Linux funcionais;
- disponibilizar uma distribuição pública para uso diário;
- garantir compatibilidade universal com aplicativos Windows, macOS ou Android;
- passthrough automático de GPU, USB ou outros dispositivos;
- execução de shell arbitrário pela IA;
- promoção automática de patches ou atualização de `main`;
- coleta externa de telemetria por padrão.

## Etapa 0 — Preparar evidência de base

- [ ] Conferir os contratos atuais do habitat, API, residente, memória e Registro Delta.
- [ ] Mapear pacotes, versões, portas, sockets, serviços, diretórios persistentes e segredos.
- [ ] Escolher um conjunto mínimo de testes que roda na base Linux atual antes de empacotar.
- [ ] Definir hardware virtual e recursos fixos para comparações: vCPU, RAM, disco, firmware, GPU virtual e rede.
- [ ] Separar resultados existentes de testes que ainda precisam ser executados.

**Aceite:** inventário com caminhos, dependências e comandos verificáveis; nenhuma credencial incluída no artefato.

## Etapa 0B — Spike descartável de virtualização

Antes de comparar bases finais, usar a imagem cloud oficial do Ubuntu Server 24.04 como um **teste temporário do hipervisor e do fluxo de boot**. Isto valida o ambiente KVM/libvirt e reduz o risco de depurar simultaneamente a base do sistema e a infraestrutura da VM; não elege Ubuntu como distribuição definitiva do DELTA.

Ferramentas adicionadas para este fluxo:
- `deploy/delta/preflight_vm.sh` — pré-voo somente de leitura para QEMU/KVM, rede libvirt, chave pública SSH e espaço de armazenamento;
- `deploy/delta/diagnosticar_vm_mvp0.sh` — diagnóstico somente de leitura de eventual domínio parcial após falha de `virt-install`;
- `deploy/vps/preparar_base_ubuntu.sh` — baixa a imagem cloud e valida seu SHA-256 contra a lista publicada no diretório oficial antes de aceitar o arquivo;
- `deploy/delta/preparar_storage_mvp0.sh` — exige confirmação para criar `delta-mvp0-storage` fora da home, por padrão em `/var/lib/libvirt/images` (ajustável por `NYXOS_DELTA_STORAGE_ROOT`), após verificar acesso de travessia para `libvirt-qemu`, espaço e checksum da imagem. Aplica ACL somente ao novo diretório; não altera a home, o pool `VPS`, serviços ou arquivos existentes;
- `deploy/delta/criar_vm_mvp0.py` — chama o provisionador KVM já existente (`nixal_vps.py`) depois de validar a imagem, espaço, domínio, rede e chave pública, exigindo confirmação interativa. Recusa armazenamento de VM dentro da home.

A primeira tentativa falhou porque `libvirt-qemu` não podia pesquisar `/home/nyxal`; não se deve usar `chmod 777` nem abrir permissões globais na home. O helper agora exige um diretório de armazenamento existente, acessível ao usuário `libvirt-qemu` e fora da home — por padrão `/var/lib/libvirt/images`. Ele não usa nem reconfigura o pool `VPS` existente, não instala pacotes e não remove arquivos. A imagem base pode permanecer em `~/NyxOS/VPS`; o provisionador só a lê para preparar o disco.

Configuração inicial: VM `delta-mvp0`, 2 vCPUs, 2048 MiB de RAM, disco QCOW2 de 16 GiB virtuais e rede NAT libvirt default. Autostart do host fica desligado por padrão. O provisionador existente cria um usuário `ubuntu` com chave SSH e sudo sem senha dentro da VM; tratar como ambiente descartável, não copiar segredos nem dados pessoais do host e não expor a VM por bridge público.

**Aceite do spike:** a VM aparece em `virsh list --all`, completa o boot, recebe endereço pela rede default e permite acesso por console/SSH. Registrar comandos e resultados reais. Se `cloud-localds`, a rede libvirt ou a chave pública não estiverem disponíveis, parar e resolver a pré-condição; não reconfigurar automaticamente o host.

Este spike não satisfaz o aceite da imagem DELTA completa, não demonstra desktop NyxOS, nem substitui a comparação de base da Etapa 1.

## Etapa 1 — Comparar bases em VM

Construir protótipos mínimos equivalentes com:

1. NixOS;
2. Fedora bootc ou solução de imagem transacional suportada.

A comparação deve usar o mesmo contrato funcional, não configurações arbitrariamente diferentes. Caso uma das opções não possa ser automatizada no ambiente disponível, registrar o bloqueio e a evidência em vez de declarar sucesso.

Medir:
- reprodutibilidade do build;
- tempo de build e de boot;
- simplicidade de instalar/atualizar pacotes e serviços;
- atualização offline ou com rede limitada;
- rollback e recuperação;
- suporte à sessão gráfica e aceleração disponível;
- compatibilidade com o ambiente Python/venv e dependências nativas da Nyxal;
- complexidade de manutenção e clareza das falhas.

**Aceite:** matriz comparativa e decisão registrada em ADR. Não escolher somente por preferência pessoal ou aparência.

## Etapa 2 — Imagem NyxOS inicializável

- [ ] Criar uma receita versionada de imagem para a base escolhida.
- [ ] Fixar fontes e versões de dependências sempre que o mecanismo permitir.
- [ ] Configurar uma sessão gráfica suportada e um usuário normal.
- [ ] Instalar o conjunto mínimo de serviços NyxOS e dependências.
- [ ] Manter a API vinculada a loopback e preservar as exigências de autenticação documentadas.
- [ ] Manter tokens e estado local fora da imagem e fora do Git.
- [ ] Criar uma tela de identificação DELTA/NyxOS sem acoplar a identidade visual ao funcionamento do runtime.
- [ ] Registrar versão/build, base, commit de origem e limitações no artefato.

**Aceite:** uma VM limpa inicia a imagem sem intervenção manual não documentada e mostra sua versão.

## Etapa 3 — Integrar Nyxal sem ampliar privilégios

- [ ] Executar o runtime sob usuário não privilegiado.
- [ ] Reutilizar os serviços e contratos existentes, sem criar outro runtime ou um segundo sistema de memória.
- [ ] Manter gateway de atuação separado da API de conversa.
- [ ] Bloquear execução arbitrária de shell e capacidade inventada por saída de modelo.
- [ ] Garantir que falha do provedor de IA não impeça o boot, a parada segura ou o diagnóstico.
- [ ] Preservar memória, configuração e Registro Delta durante uma atualização de imagem suportada.
- [ ] Verificar que logs e endpoints de diagnóstico não revelam tokens, cabeçalhos secretos ou dados sensíveis.

**Aceite:** Nyxal inicia, responde a um health check, registra eventos sem conceder autorização e pode ser interrompida sem perder o estado confirmado.

## Etapa 4 — Recuperação e atualização

- [ ] Instalar uma versão de teste e registrar sua identificação.
- [ ] Simular uma atualização válida.
- [ ] Simular um artefato inválido e confirmar que ele é rejeitado antes da ativação.
- [ ] Simular uma falha no health check pós-atualização.
- [ ] Executar rollback para a versão anterior.
- [ ] Confirmar que configuração/estado não são sobrescritos por arquivos da imagem.
- [ ] Verificar se o mecanismo de recuperação funciona sem rede, UI ou inferência da Nyxal.

**Aceite:** testes demonstram tanto caminho feliz quanto falha controlada; artefatos, transições e erros ficam identificados no log.

## Etapa 5 — Testes mínimos de regressão

### Boot e serviços
- [ ] Imagem inicia em VM limpa.
- [ ] Sessão gráfica pode abrir e encerrar.
- [ ] API e residente mostram estado esperado no systemd.
- [ ] Reiniciar a VM preserva o estado que deve persistir.
- [ ] Parar Nyxal não impede recuperação ou desligamento do sistema.

### Segurança
- [ ] API não escuta em uma interface pública por padrão.
- [ ] Chamadas não autenticadas a rotas protegidas são recusadas.
- [ ] Processo Nyxal não tem UID 0.
- [ ] Operação não registrada é negada antes do executor.
- [ ] Saídas de erro não contêm segredos.
- [ ] Diretórios de dados e credenciais têm permissões documentadas.
- [ ] Não há segredos, tokens ou dumps pessoais no artefato ou no Git.

### Integridade e manutenção
- [ ] A imagem referencia a origem/commit usado para construir.
- [ ] Dependências e limitações estão documentadas.
- [ ] Testes do habitat e da API continuam executáveis.
- [ ] O relatório distingue testes automatizados, verificações manuais e itens não testados.
- [ ] A receita pode ser repetida por outra pessoa a partir do documento.

## Estrutura sugerida para o relatório de validação

| Campo | Conteúdo obrigatório |
|---|---|
| Identificação | ID da imagem, commit, base e data |
| Ambiente | Hipervisor, vCPU, RAM, disco, GPU virtual e rede |
| Build | Comando/receita, duração, status e avisos |
| Boot | Tempo observado, login, desktop e erros |
| NyxOS | Estado das unidades, health checks e logs |
| Segurança | Resultado de cada teste, sem copiar segredos |
| Persistência | Estado antes/depois de reinício e atualização |
| Recuperação | Artefato anterior, gatilho, rollback e resultado |
| Limitações | Aplicações não avaliadas e hardware não testado |

## Condições para avançar

O MVP-0 só pode ser considerado aprovado se:
1. todos os testes obrigatórios forem executados;
2. falhas conhecidas estiverem registradas, sem ser classificadas como sucesso;
3. houver evidência de boot, persistência, política de permissões e recuperação;
4. a decisão sobre a base tiver justificativa documentada;
5. não houver mutação automática de `main` nem de configurações de produção.

Depois do aceite, a próxima RFC pode detalhar o primeiro ciclo de desktop e catálogo unificado. A integração Wine/Proton, Waydroid e Darling entra em etapas separadas, cada uma com seu próprio conjunto de compatibilidade e segurança.

## Regra de status

Use somente estes estados no relatório:
- **PASSOU:** o teste foi executado e atendeu ao critério.
- **FALHOU:** o teste foi executado e não atendeu.
- **BLOQUEADO:** dependência ou ambiente impediu a execução; registrar evidência.
- **NÃO EXECUTADO:** não há evidência de tentativa.

A existência de uma receita, documento ou teste escrito não prova que o teste tenha passado.
