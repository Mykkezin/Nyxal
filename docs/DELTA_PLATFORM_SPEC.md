# DELTA — Especificação de Plataforma

**Estado:** proposta inicial para revisão técnica  
**Branch de trabalho:** `feat/delta-platform-foundation-20261027`  
**Escopo desta versão:** arquitetura e critérios da primeira imagem experimental; não cria kernel próprio nem altera o comportamento de produção da Nyxal.

## 1. Identidade e nomes

- **DELTA** é o nome do ecossistema e produto completo.
- **NyxOS** é o sistema operacional, a experiência de boot/desktop, os serviços e a política que organiza o computador.
- **Nyxal** é o runtime de inteligência integrado: conversa, raciocínio, memória, ferramentas, observabilidade e evolução governada.
- **Registro Delta** continua sendo o subsistema existente que registra mudanças auditáveis de estado. O uso de DELTA como nome do produto não substitui nem renomeia automaticamente esse módulo.

## 2. Decisão arquitetural principal

O DELTA será construído primeiro como um sistema operacional controlado pelo projeto sobre o kernel Linux. Não será iniciada uma fusão de kernels NT/Linux nem uma implementação de kernel própria.

“Sistema operacional próprio” será considerado alcançado progressivamente por uma combinação verificável de:
1. imagem inicializável reproduzível;
2. configuração e serviços versionados;
3. desktop e identidade visual integrados;
4. política de segurança e permissões documentada;
5. instalação, atualização e recuperação testáveis;
6. compatibilidade medida por matriz de hardware/software;
7. runtime Nyxal integrado por contratos estáveis e permissões mínimas.

Substituir o kernel Linux será uma hipótese futura, sujeita a um requisito demonstrado, análise de custo/risco, modelo de ameaças, protótipo e aprovação específica.

## 3. Arquitetura de referência

```text
DELTA — PRODUTO / ECOSSISTEMA
└── NyxOS — boot, sessão e experiência do sistema
    ├── Desktop Wayland / shell / catálogo de aplicativos
    ├── Serviços de sistema e atualização/recuperação
    ├── Integração de aplicações
    │   ├── Linux: execução nativa ELF
    │   ├── Windows: Wine/Proton quando compatível
    │   ├── Android: Waydroid quando o host for compatível
    │   ├── macOS: Darling experimental ou virtualização permitida
    │   └── SO completo isolado: KVM/QEMU quando necessário
    ├── Camada de confiança
    │   ├── identidade/permissões por serviço
    │   ├── broker de capacidades para operações privilegiadas
    │   ├── sandbox para experimentos e código não confiável
    │   └── trilha de auditoria / atualização autenticada
    ├── Nyxal AI Runtime — espaço de usuário, sem root
    │   ├── inferência e roteamento de provedores
    │   ├── memória, conhecimento e contexto
    │   ├── ferramentas, observabilidade e voz
    │   └── AE/LLC: experimentação e aprendizagem governadas
    └── Registro Delta — histórico de mudanças observáveis
        ↓ interfaces estáveis do sistema
Kernel Linux + drivers suportados
        ↓
Hardware e firmware
```

O diagrama estabelece fronteiras lógicas e de confiança. Ele não exige transformar todo módulo em microserviço; componentes só devem virar processos separados quando isso trouxer isolamento, confiabilidade ou manutenção mensuráveis.

## 4. Princípios não negociáveis

1. **Reutilizar antes de reimplementar.** Preferir drivers Linux existentes, APIs documentadas, componentes upstream e formatos abertos.
2. **Não executar texto do modelo como shell.** Intenção, plano, autorização e execução são etapas distintas.
3. **Privilégio mínimo.** O runtime Nyxal não é root e não carrega módulos do kernel. Operações privilegiadas, quando necessárias, passam por um broker pequeno, enumerado e independente da decisão do modelo.
4. **Negar por padrão.** Ação não registrada, origem não autorizada, argumentos desconhecidos ou política indisponível resultam em recusa segura.
5. **Isolar código não confiável.** Experimentos, plugins não auditados e aplicações de risco não recebem segredos, diretórios de produção ou acesso irrestrito ao host.
6. **Evolução reversível.** Mudanças precisam de artefato versionado, testes, evidência, promoção explícita e plano de rollback.
7. **Persistência sem falsa autoridade.** Memória, evento Delta, hipótese ou resultado experimental são dados; não concedem autorização.
8. **Compatibilidade como evidência.** “Compatível” significa que um conjunto identificado de versões e hardware passou em testes reproduzíveis, não que todo aplicativo funcionará.
9. **Recuperação sem IA.** Boot, parada, recuperação e reversão devem continuar possíveis se a UI, a rede ou os provedores de inferência falharem.
10. **Sem promessas sem teste.** Desempenho, baixa latência, segurança, isolamento e recuperação devem ser medidos no alvo declarado.

## 5. Sistema base e empacotamento

A seleção da base permanece aberta até um experimento comparativo. As opções iniciais para avaliação são:

- **NixOS:** configuração declarativa e gerações reversíveis; precisa validar ergonomia, drivers e GPU/ROCm do hardware-alvo.
- **Fedora bootc ou imagem transacional equivalente:** sistema por imagem e fluxo de atualização/rollback; precisa validar desktop, GPU, ferramentas de desenvolvimento e cobertura do host.

O experimento deve usar a mesma lista de serviços NyxOS, os mesmos testes e critérios comparáveis. A decisão será documentada em uma ADR antes de estabelecer a distribuição principal. A aplicação deve evitar dependência desnecessária de caminhos exclusivos de uma distribuição.

A imagem inicial deve manter separados:
- arquivos base/versionados do sistema;
- configuração local;
- estado persistente da Nyxal;
- logs e eventos;
- credenciais e tokens;
- artefatos de experimento.

Nenhum segredo ou estado pessoal deve ser incluído na imagem ou no Git.

## 6. Modelo de compatibilidade

### Linux
Executar aplicações ELF nativamente sobre o kernel e as bibliotecas suportadas pela base escolhida. Registrar dependências e versões.

### Windows
Usar Wine/Proton e componentes de tradução gráfica, como DXVK ou vkd3d-proton, somente quando suportados pela aplicação. Para programas que exigem kernel/driver Windows real, testar uma VM completa quando houver suporte legal e de hardware. Anti-cheats, DRM, drivers, periféricos e aplicativos corporativos devem ter status individual; nenhuma compatibilidade universal é prometida.

### Android
Avaliar Waydroid como integração baseada no kernel Linux, com verificação de namespaces, binder, gráficos, áudio, rede e hardware. Ausência de requisito do host deve produzir estado “não suportado”, não simulação de sucesso.

### macOS
Tratar Darling como pesquisa experimental para casos delimitados. Para executar um sistema macOS completo, considerar apenas hardware, imagens e licenças permitidos pelas condições aplicáveis. Não comprometer o desenho do desktop principal por causa de compatibilidade incompleta.

### Sistemas operacionais completos
Quando for necessária compatibilidade mais fiel ou isolamento, usar virtualização suportada (por exemplo KVM/QEMU), aceitando os custos e limites de GPU, USB, áudio e integração de janelas. Passthrough de dispositivo não será habilitado automaticamente pela IA.

## 7. Desktop único

O primeiro desktop usará uma base Wayland existente em vez de iniciar por um compositor gráfico próprio. A seleção entre shell próprio e desktop existente será baseada em protótipo, acessibilidade, estabilidade, custo de manutenção e suporte a GPU.

A experiência integrada terá como metas:
- catálogo unificado de aplicações;
- janelas e áreas de trabalho coerentes;
- clipboard e troca de arquivos com política explícita;
- notificações, atalhos, áudio e configurações integrados;
- sinalização visível de aplicações isoladas ou virtualizadas;
- possibilidade de revogar integrações entre domínios.

Janelas de VMs podem exigir protocolos de guest integration, streaming ou remote desktop. Elas não se tornam janelas nativas automaticamente só porque compartilham a tela física.

## 8. Nyxal como inteligência do sistema

A Nyxal será o plano de inteligência, não o árbitro final de segurança. Suas responsabilidades podem incluir:
- observar recursos e serviços por interfaces de leitura definidas;
- explicar o estado do sistema e diagnosticar falhas;
- propor ajustes e produzir planos estruturados;
- invocar capacidades explícitas, com escopo e resultado observável;
- preparar patches e executar testes em ambientes descartáveis;
- comparar resultados com uma baseline e conservar proveniência;
- fornecer interface conversacional, voz e assistência.

Não poderá, por decisão do modelo:
- ganhar acesso root ou inventar novas capacidades;
- contornar autenticação ou pedir a um serviço para ignorá-la;
- gravar diretamente na configuração autoritativa do SO;
- modificar kernel, boot ou branch estável;
- promover seu próprio experimento para produção;
- apagar logs ou alterar registros de auditoria;
- considerar a memória ou uma saída de modelo como autorização.

O pipeline de evolução permanece: necessidade observada → hipótese → artefato isolado → baseline → teste → comparação → evidência → proposta → autorização independente → integração → rollback disponível.

## 9. Segurança e atualização

Cada serviço precisa declarar identidade, entradas, permissões, diretórios, conexões, limites de recursos, comportamento de erro e forma de desligamento. A API conversacional não deve ser a fronteira final para operações privilegiadas.

A atualização do sistema deverá, quando suportada pela base escolhida:
1. verificar origem, assinatura e integridade do artefato;
2. validar compatibilidade e espaço livre;
3. instalar em estágio separado ou geração nova;
4. preservar dados de usuário;
5. verificar saúde após reinicialização;
6. registrar a transição no histórico;
7. oferecer rollback verificável se o health check falhar.

O rollback não apaga a causa nem os logs do erro. Segredos ficam fora do Git e dos relatórios públicos.

## 10. Observabilidade e prevenção de obsolescência

O projeto manterá:
- versões e hashes explícitos para releases e artefatos;
- dependências identificadas e inventário/SBOM quando aplicável;
- matriz de hardware, GPU, drivers, firmware e aplicações testadas;
- testes de regressão por subsistema;
- política de atualização de dependências e análise de avisos de segurança;
- changelog, problemas conhecidos e decisões arquiteturais;
- imagens de CI reproduzíveis e caminho de recuperação testado;
- telemetria desativada por padrão quando depender de envio externo.

“Não caducar” significa ter manutenção contínua, contratos claros e migração testada — não congelar dependências indefinidamente nem prometer compatibilidade eterna.

## 11. O que esta especificação não autoriza

Este documento não:
- declara a distribuição DELTA pronta;
- prova que algum aplicativo Windows/macOS/Android funcione no computador-alvo;
- cria ou substitui um kernel;
- autoriza mudança automática de `main`;
- cria M6/AE6 automaticamente;
- habilita execução física ou de shell arbitrária;
- afirma que testes foram executados quando ainda não foram.

## 12. Referências internas

- `README.md`
- `docs/ARQUITETURA_SISTEMA_NYXOS.md`
- `docs/SEGURANCA_API_NYXAL.md`
- `docs/AUTONOMIA_E_AUTOREPARO_NYXAL.md`
- `M5_HABITAT_NYXOS.md`
- `ORDEM_ENGENHARIA_NYXOS.md`
- `FECHAMENTO_ENGENHARIA_NYXOS.md`
