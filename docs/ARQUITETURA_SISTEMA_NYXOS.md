# Arquitetura de Sistema do NyxOS — limites e evolução

**Estado:** RFC de arquitetura para revisão  
**Base observada:** `main`, documentação do habitat M5.1–M5.24 e unidades `systemd` atuais  
**Objetivo:** evoluir o habitat NyxOS para um sistema operacional distribuível, reproduzível e recuperável sem criar um kernel próprio antes de demonstrar uma necessidade técnica incontornável.

## 1. Decisão central

**NyxOS deve primeiro tornar-se um sistema operacional próprio sobre o kernel Linux; não deve começar como um kernel novo.**

“Sistema operacional próprio” tem três sentidos diferentes, que não devem ser confundidos:

1. **Habitat e experiência NyxOS:** runtime, interface, voz, memória, ferramentas, observabilidade e serviços integrados sobre uma instalação Linux. Esta linha já existe no repositório.
2. **Produto de sistema operacional NyxOS:** imagem inicializável, configuração declarativa, conjunto de pacotes controlado, política de segurança, atualização autenticada, recuperação e matriz de hardware suportada. Este é o próximo objetivo de plataforma a provar.
3. **Kernel NyxOS próprio:** substituição do kernel Linux. É uma hipótese de longo prazo que só deve avançar se testes demonstrarem um requisito essencial que o kernel Linux, seus módulos, políticas ou interfaces não consigam satisfazer com custo e risco aceitáveis.

O nome NyxOS pode designar um produto de sistema operacional mesmo mantendo o kernel Linux. Distribuição, userland, configuração, serviços, atualização e experiência de boot já compõem trabalho substancial e verificável; escrever um kernel não é pré-requisito para controlar essas camadas.

Esta RFC **não cria automaticamente M6, AE6, autoridade de integração, execução física automática ou permissão para modificar `main`**. Ela propõe decisões para revisão explícita.

## 2. Evidências do estado atual

O repositório já estabelece que:

- O habitat M5.1–M5.24 é persistente, observável e modular sobre o hospedeiro, sem kernel próprio nesta etapa.
- `nyxal-api.service` e `nyxos-residente.service` são unidades separadas; `nyxos.target` agrupa a residência.
- As unidades observadas usam o ambiente virtual do projeto e já incluem algumas proteções de serviço, como `NoNewPrivileges=true`, `PrivateTmp=true` e `UMask=0077`.
- O gateway de atuação do host define contratos tipados, allowlist, validação antes do executor, modo dry-run e proibição de shell arbitrário.
- A engenharia do habitat foi fechada na fase M5.24; a próxima evolução deve vir de uma lacuna operacional real, com objetivo mensurável, contrato, autoridade, reversibilidade, testes, promoção e rollback.

Referências internas:
- `M5_HABITAT_NYXOS.md`
- `M5_9_RESIDENCIA_LINUX.md`
- `ORDEM_ENGENHARIA_NYXOS.md`
- `M5_10_GATEWAY_ATUACAO_HOST.md`
- `FECHAMENTO_ENGENHARIA_NYXOS.md`
- `deploy/systemd/nyxos.target`
- `deploy/systemd/nyxal-api.service`
- `deploy/systemd/nyxos-residente.service`

Essas bases são úteis, mas **não comprovam ainda** uma imagem NyxOS inicializável, atualizações transacionais de todo o sistema, recuperação do boot, isolamento de sistema entre domínios de confiança ou uma camada genérica e auditada de acesso a dispositivos. Esses itens devem ser tratados como trabalho futuro, não como recursos concluídos.

## 3. Arquitetura-alvo e fronteiras

```text
┌──────────────────────────────────────────────────────────────┐
│ ESPAÇO DO USUÁRIO                                             │
│ NyxOS Display / shell / acessibilidade / configurações        │
└─────────────────────────────┬────────────────────────────────┘
                              │ API autenticada
┌─────────────────────────────▼────────────────────────────────┐
│ SERVIÇOS NYXOS NÃO PRIVILEGIADOS                              │
│ API · Runtime residente · memória/Delta · áudio/voz           │
│ provedores de inferência · observabilidade · atualizador UI   │
│ Identidades/UIDs, permissões e dados separados por serviço    │
└──────────────┬───────────────────────┬───────────────────────┘
               │ requisição tipada     │ artefato/dado
               ▼                       ▼
┌────────────────────────────┐  ┌──────────────────────────────┐
│ BROKER DE CAPACIDADES      │  │ WORKER DE EXPERIMENTOS       │
│ privilegiado só se preciso │  │ sandbox descartável          │
│ allowlist pequena          │  │ sem segredos nem credenciais │
│ política fora do modelo IA │  │ limites de CPU/RAM/tempo/I/O  │
└──────────────┬─────────────┘  └──────────────────────────────┘
               │ interfaces de SO específicas e limitadas
┌──────────────▼───────────────────────────────────────────────┐
│ USERLAND / BASE DO SISTEMA                                   │
│ systemd · udev · logind · PipeWire · rede · journal · IPC     │
│ ferramentas administrativas e políticas do sistema            │
└──────────────────────────────┬───────────────────────────────┘
                               │ syscalls e interfaces estáveis
┌──────────────────────────────▼───────────────────────────────┐
│ KERNEL LINUX + DRIVERS UPSTREAM / MÓDULOS APROVADOS           │
│ scheduler · memória · VFS · rede · áudio · USB · GPU · hwmon  │
└──────────────────────────────┬───────────────────────────────┘
                               │ barramentos e controladores
┌──────────────────────────────▼───────────────────────────────┐
│ HARDWARE + FIRMWARE                                           │
│ CPU · RAM · armazenamento · GPU/NPU · áudio · sensores · fans │
└──────────────────────────────────────────────────────────────┘
```

O diagrama descreve fronteiras lógicas e de confiança; não exige que cada módulo lógico seja imediatamente um processo independente. Separar contratos primeiro e multiplicar processos depois evita microserviços desnecessários.

### 3.1 Hardware e firmware

- Permanecem sob firmware da plataforma e interfaces de hardware conhecidas.
- O NyxOS mantém uma matriz explícita de hardware suportado, versões de firmware e limitações conhecidas.
- Não se escreve um driver próprio se um driver Linux upstream ou uma interface padrão já atende ao requisito.
- Operações físicas destrutivas, perigosas ou difíceis de reverter não são expostas como ferramentas genéricas da IA.

### 3.2 Kernel e drivers

- O kernel Linux permanece a fronteira de privilégio máximo.
- O NyxOS consome syscalls e interfaces existentes: dispositivos em `/dev`, interfaces de sensores, APIs de áudio, rede e gerenciamento de sessão, com permissões mínimas.
- Serviços normais nunca carregam módulos de kernel nem recebem acesso irrestrito a dispositivos.
- Leitura de sensores e escrita em atuadores são capacidades diferentes. A permissão de ler telemetria não concede permissão de comandar ventoinhas, energia ou outros dispositivos.
- Se surgir uma lacuna, primeiro testar configuração do kernel, driver upstream, módulo externo controlado ou serviço de user space. Desenvolvimento de driver/kernel entra num processo técnico separado, com testes de compatibilidade e recuperação.

### 3.3 Base do sistema e serviços privilegiados

- `systemd` supervisiona ciclo de vida, dependências, reinício, logs e limites dos processos.
- `udev`, `logind`, `PipeWire` e interfaces de rede continuam sendo mecanismos do sistema operacional, não subsistemas duplicados pelo NyxOS.
- A administração do host deve passar por um **broker de capacidades** pequeno e independente do runtime de IA, e só existir quando a operação realmente exige privilégio adicional.
- O broker roda com identidade própria, recebe contratos estruturados, aplica política, limita argumentos, registra resultado e expõe somente operações enumeradas.
- Se uma ação não está registrada, sua resposta é negar. Configuração ou texto produzido pelo modelo não podem acrescentar executores privilegiados.
- IPC local deve usar Unix domain sockets com permissões explícitas; operações remotas usam autenticação e transporte protegido. Um endpoint local não deve ser tratado como confiável só por ser local.

**Regra:** privilegiar o menor mecanismo confiável possível. O broker não deve virar um shell remoto nem uma API de root genérica.

### 3.4 Runtime de IA

O runtime de IA é um processo de user space sem privilégios de administrador. Ele coordena intenção, contexto, seleção de capacidades, inferência e avaliação, mas **não é a autoridade final para permitir ações**.

Deve ter:

- identidade de sistema própria e diretórios de dados definidos;
- acesso explícito somente aos arquivos e sockets necessários;
- interface de capacidade tipada, validada fora do modelo;
- limites de CPU, memória, tempo e número de operações concorrentes;
- logs com identificador de correlação, origem, política aplicada, resultado e duração;
- separação entre texto gerado, decisão candidata e autorização efetiva;
- nenhuma permissão de escrita em artefatos de boot, configuração autoritativa do SO ou branch estável;
- credenciais de provedores e integrações isoladas do histórico conversacional e nunca injetadas em workers experimentais.

O processo de inferência pode ser local ou remoto. A escolha Ollama/vLLM/serviço externo não modifica o modelo de autoridade: o provedor recebe apenas o contexto necessário; nunca ganha acesso direto a drivers, shell privilegiado ou ao broker.

### 3.5 API, interface, voz, memória e Delta

- Interface e API são pontos de apresentação/entrada, não fronteiras de autorização.
- A API valida identidade, tamanho, tipo e escopo antes de chamar capacidades.
- Voz/STT/TTS permanecem adaptadores de borda. Detecção de fala, texto reconhecido ou resposta sintetizada nunca equivalem a consentimento para uma ação de alto risco.
- Memória, estado operacional e Delta preservam proveniência, versionamento e permissões; memória persistente não se torna automaticamente fonte de autoridade.
- Dados pessoais, tokens, chaves, gravações e logs sensíveis exigem retenção e controles próprios.
- A indisponibilidade da UI ou do provedor de inferência não deve impedir o usuário de parar serviços ou recuperar o sistema.

### 3.6 Experimentos e autoaperfeiçoamento

- Workers experimentais são tratados como código não confiável, executado fora do processo residente.
- Primeiro estágio: runner efêmero do CI ou ambiente isolado equivalente; sem segredos, credenciais, permissões de produção ou acesso de escrita ao sistema instalado.
- Para execução local, avaliar namespaces/cgroups e sandbox apropriada, com bloqueio de rede por padrão e política explícita de arquivos/dispositivos.
- Resultados são dados de evidência, não comandos de implantação.
- O ciclo AE/LLC pode recomendar uma alteração, mas não escolhe sozinho sua autoridade, não promove código, não muda kernel e não atualiza o sistema estável.
- A instalação de uma nova versão exige verificação de assinatura/proveniência, validação de testes e política de promoção separada.

## 4. Contratos entre camadas

| Fronteira | Interface permitida | Proibido |
|---|---|---|
| UI → API | API versionada, autenticação, esquema explícito | Acesso direto ao banco de estado ou execução de shell |
| Runtime → ferramenta | Registro de capacidades tipadas | Executar texto gerado como comando |
| Runtime → broker | Socket local autenticado, ações enumeradas | Chamada genérica de root, comando arbitrário ou executor improvisado |
| Serviço → armazenamento | Diretório próprio, ACL/permissões e esquema versionado | Escrita em arquivos de outro domínio sem contrato |
| Runtime → inferência | Adaptador de provedor, timeout, limite de contexto | Delegar a autoridade de autorização ao modelo remoto |
| Experimento → avaliação | Artefato identificado por hash + resultado estruturado | Segredos, tokens de produção, acesso irrestrito ao host |
| Userland → driver | Interfaces documentadas do kernel / APIs do sistema | Acesso privilegiado sem necessidade demonstrada |
| Atualizador → SO | Artefato assinado, verificação, staging, health check e rollback | Atualização automática disparada por hipótese da IA sem autorização |
| NyxOS → hardware | Drivers Linux e serviços de dispositivo com política | Driver próprio por padrão ou controle físico irrestrito |

Todos os contratos devem definir: versão, identidade do chamador, entradas aceitas, permissões, timeouts, tamanho máximo, estados de erro, dados registrados, compatibilidade e comportamento quando o provedor ou dispositivo está ausente.

## 5. Empacotamento e forma do sistema operacional

Antes de escolher uma distribuição definitiva, manter o runtime compatível com Linux e systemd, sem acoplamento a caminhos específicos de uma única distro sempre que isso for viável.

Comparar duas opções com protótipos reproduzíveis:

- **NixOS:** forte alinhamento com configuração declarativa, gerações e rollback; exige familiaridade com Nix e validação cuidadosa de drivers e do stack AMD/ROCm do hardware-alvo.
- **Imagem baseada em Fedora bootc ou mecanismo equivalente de imagem transacional:** abordagem de sistema por imagem, com operações de atualização e recuperação; requer verificar maturidade e cobertura da combinação exata de desktop, GPU e hardware pretendida.

Não escolher agora apenas por estética ou preferência. Criar um spike em VM para cada opção com os mesmos testes e pontuar: reprodutibilidade, rollback, drivers/GPU, atualização offline, tamanho, tempo de build, suporte, manutenção e ergonomia do desktop. Manter a aplicação fora da lógica específica do empacotador.

A primeira imagem de NyxOS deve conter:
- boot e sessão recuperáveis;
- sistema base e serviços versionados;
- instalador/desinstalador ou mecanismo de implantação documentado;
- configuração separada dos dados mutáveis;
- logs e diagnóstico acessíveis;
- estratégia de backup/migração de dados;
- canal de atualização verificável;
- modo de recuperação que funcione sem runtime, UI ou rede.

A meta inicial é uma **imagem de sistema operacional controlada pelo projeto**, não uma distribuição independente de pacotes desde o primeiro dia.

## 6. Plano de evolução proposto

### Etapa A — Contrato e inventário de privilégios

**Objetivo:** conhecer e documentar os domínios de confiança reais antes de reempacotar.

Entregáveis:
- inventário de unidades, usuários, grupos, portas, sockets, arquivos, permissões e diretórios graváveis;
- mapa de dependências e fluxos de dados;
- threat model com abuso do modelo, prompt injection, comprometimento de provedor, worker malicioso, API exposta, dispositivo comprometido e atualização defeituosa;
- classificação por serviço: público, usuário, interno, privilegiado ou experimental;
- ADRs para comunicação, armazenamento, capabilities, inferência e política de atualização.

Aceite:
- cada serviço tem identidade e motivo de acesso documentados;
- nenhum serviço precisa de privilégios implícitos;
- dados de configuração, estado, logs e segredos possuem destinos distintos;
- riscos conhecidos têm teste ou mitigação registrada.

### Etapa B — Hardening das unidades Linux

**Objetivo:** reduzir o raio de impacto preservando o comportamento atual.

Ações propostas, uma a uma e com testes:
- limitar caminhos graváveis aos diretórios necessários;
- usar `ProtectSystem`, `ProtectHome`, `PrivateDevices`, `RestrictAddressFamilies`, filtros de syscalls, limites de recursos e políticas equivalentes quando suportados e compatíveis;
- executar cada unidade com o menor privilégio possível;
- distinguir serviços do usuário e serviços do sistema; usar um serviço de sistema separado somente para capacidades que realmente exijam privilégio;
- verificar listeners, CORS, autenticação, exposição remota e credenciais;
- automatizar teste das unidades e inspeção de configuração de segurança.

Essas opções não devem ser copiadas cegamente: disponibilidade e semântica variam entre versões e entre system manager de sistema e de usuário. Toda restrição deve ser comprovada em boot, reinício, áudio, inferência, atualização e desligamento.

Aceite:
- testes de regressão do M5 continuam verdes;
- cada unidade possui perfil de permissões documentado;
- teste automatizado demonstra que operações não permitidas falham antes do executor;
- falhas dos serviços não viram escalada de privilégios nem perda de dados persistentes.

### Etapa C — Contratos e broker de capacidades

**Objetivo:** padronizar atuação no sistema sem centralizar poder excessivo no runtime.

Entregáveis:
- esquema versionado para requisições e respostas;
- política de risco e autorização fora do modelo;
- broker mínimo, se a auditoria demonstrar que é necessário;
- catálogo de operações por dispositivo/domínio;
- dry-run, trilha de auditoria e proteção contra replay onde fizer sentido;
- mecanismo de parada e cancelamento de ações longas.

Aceite:
- catálogo vazio por padrão em instalação nova;
- ação desconhecida, argumentos extras, tipos errados e caller sem permissão são negados;
- teste de prompt injection não consegue inventar uma nova capacidade;
- todos os resultados informam decisão de política, execução real/não executada e correlação;
- revogar uma capacidade não requer alterar o modelo de IA.

### Etapa D — Perfil de sistema NyxOS reproduzível

**Objetivo:** produzir uma instalação configurável, repetível e recuperável.

Entregáveis:
- seleção comparativa de mecanismo de imagem;
- manifesto das dependências e configuração de sistema;
- empacotamento/versionamento de serviços e assets;
- diretórios de configuração e dados persistentes definidos;
- ambiente de desenvolvimento e imagem de teste reproduzíveis;
- SBOM e registro de proveniência dos artefatos.

Aceite:
- duas construções a partir do mesmo commit e lock/configuração produzem os mesmos identificadores de versão e dependências; artefatos byte-a-byte idênticos são desejáveis quando o ferramental permitir;
- instalação limpa em VM e atualização a partir da versão anterior são testadas;
- dados do usuário sobrevivem a atualização e rollback conforme política explícita;
- a imagem não exige segredos embutidos.

### Etapa E — Boot, atualização e recuperação

**Objetivo:** garantir que o NyxOS não dependa de o próprio runtime se reparar.

Entregáveis:
- imagem inicializável de teste;
- verificação de integridade/proveniência;
- atualização em staging ou mecanismo transacional;
- health check após ativação;
- retorno automático ou guiado à última versão saudável;
- mídia ou modo de recuperação independente.

Aceite:
- boot e login são validados em CI com VM;
- atualização incompleta ou falha de health check não deixa o equipamento inutilizável;
- rollback comprovado em cenários de versão incompatível, serviço essencial ausente e configuração inválida;
- recuperação documentada e exercitada sem rede.

### Etapa F — Hardware e drivers

**Objetivo:** formalizar suporte a hardware mantendo o kernel Linux.

Entregáveis:
- matriz de CPU/GPU/áudio/Bluetooth/rede/sensores/energia;
- adaptadores de user space para interfaces padronizadas;
- telemetria somente leitura inicialmente;
- ações de atuador isoladas por política e autorização;
- testes de ausência, falha, timeout e dados fora de faixa.

Aceite:
- dispositivo ausente ou defeituoso não derruba o runtime;
- leitura e escrita possuem permissões independentes;
- controle físico permanece desabilitado até haver necessidade, método reversível e validação no equipamento;
- módulos/firmware usados e limitações de hardware ficam identificados na release.

### Etapa G — Decisão sobre kernel

Não iniciar um kernel próprio por calendário, branding ou desejo de autonomia.

Abrir um estudo de viabilidade apenas quando houver:
1. requisito essencial escrito e mensurável;
2. demonstração reproduzível de que kernel Linux upstream + configuração + drivers + serviços não o satisfazem;
3. análise de alternativas, inclusive contribuição upstream;
4. estimativa explícita de manutenção de arquiteturas de CPU, drivers, segurança, boot, depuração e CVEs;
5. protótipo isolado com recuperação e testes;
6. decisão humana explícita sobre custos e risco operacional.

Mesmo nessa etapa, a ordem preferencial é: configuração do kernel existente → correção/contribuição upstream → driver ou módulo especializado → integração com o sistema → somente depois avaliar um kernel divergente. Um kernel próprio não herda automaticamente o ecossistema de drivers, correções e compatibilidade do Linux.

## 7. Métricas de prontidão

Antes de considerar o NyxOS um produto de sistema operacional:

- **Permissões:** 100% das unidades inventariadas; nenhum processo comum executando como root sem justificativa aprovada.
- **Negação por padrão:** 100% dos testes de ação desconhecida, caller não autorizado e argumentos inválidos são negados sem chamar o executor.
- **Reinício:** serviços essenciais toleram encerramento e reinício forçados sem corromper seus estados persistentes.
- **Recuperação:** 10/10 tentativas de rollback no conjunto de cenários definidos retornam a uma versão inicializável.
- **Atualização:** toda release tem versão, hash, proveniência e resultado de testes registrado.
- **Reprodutibilidade:** dependências, configuração e procedimento de build estão versionados; desvios de artefato são explicáveis.
- **Isolamento experimental:** workers não recebem secrets e não podem modificar stable, dados do usuário ou serviços instalados.
- **Compatibilidade:** a matriz de hardware lista o que foi efetivamente testado, o que é experimental e o que não é suportado.
- **Operabilidade:** diagnóstico e recuperação são possíveis sem o modelo, o runtime, a UI ou a rede.

Os números são alvos propostos para as provas iniciais, não afirmações sobre a situação atual do projeto.

## 8. Não objetivos desta RFC

- escrever ou substituir o kernel Linux;
- criar drivers próprios sem necessidade provada;
- migrar imediatamente a máquina principal para outra distribuição;
- trocar todas as unidades `systemd --user` por serviços globais;
- dividir todo o runtime em microserviços;
- conceder poderes adicionais ao runtime de IA;
- habilitar captura contínua, wake word ou atuação física automática;
- criar M6 ou AE6 automaticamente;
- integrar esta proposta diretamente em `main`.

## 9. Próxima ação recomendada

Começar pela **Etapa A**, produzindo um inventário auditável dos serviços, identidades, portas, arquivos, permissões e acessos a hardware. Em paralelo, fazer hardening incremental de uma unidade de cada vez com testes de regressão. Só depois construir duas provas de imagem em VM e escolher a estratégia de distribuição.

A primeira definição importante do NyxOS é a fronteira de autoridade, não o nome do kernel. O produto deverá continuar operável, auditável e recuperável mesmo quando todos os modelos de IA estiverem desligados.

## Referências técnicas

- Linux kernel documentation: https://docs.kernel.org/
- systemd execution environment e opções de sandbox: https://www.freedesktop.org/software/systemd/man/latest/systemd.exec.html
- Manual do NixOS, configuração declarativa e gerações: https://nixos.org/manual/nixos/stable/
- Repositório Nyxal: https://github.com/Mykkezin/Nyxal
