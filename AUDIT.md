# AUDIT.md — Auditoria estática da `main`

**Data:** 2026-11-14  
**Repositório:** [Mykkezin/Nyxal](https://github.com/Mykkezin/Nyxal)  
**Branch auditada:** `main`  
**Commit-base:** `a8d9d64ea2169ffba8ecd901bc92325b84bc07eb`  
**Escopo:** diagnóstico somente leitura; nenhum código ou configuração operacional foi alterado nesta auditoria.

## 1. Resumo executivo

A `main` contém uma base funcional relevante — API local, interface única, núcleo conversacional, memória, runtime residente, governança, serviços systemd e workflows de validação. O principal problema estrutural não é ausência de componentes: é a distância entre o número de módulos versionados e a existência de um caminho de execução único, explícito e reproduzível.

Os riscos mais importantes encontrados:

1. **Inicialização condicionalmente quebrável:** o launcher aceita o adaptador HTTP nativo do Ollama sem o pacote Python `ollama`, mas o compositor importado pelo núcleo conversacional exige `import ollama` diretamente. O preflight pode aprovar um ambiente que depois falha ao importar a API.
2. **Manifesto de autorrepresentação desatualizado:** `planta_nixal/planta.json` ainda descreve a arquitetura 56.4.2 como em construção e a camada conversacional como não iniciada, embora a documentação atual declare M5.24 e a linha conversacional 56.5.x. O manifesto é consumido por código, portanto a divergência pode afetar respostas de autorrepresentação.
3. **Instalação e dependências pouco reprodutíveis:** não há manifesto central de dependências da aplicação nem um exemplo completo de ambiente; os serviços assumem caminhos fixos no diretório pessoal.
4. **Documentação de provedores divergente:** `EXECUCAO_LOCAL.md` descreve seleção explícita de OpenAI/Grok pela API de chat; os testes e o roteador atual afirmam que o chat público força Nyxal local e mantém os provedores externos bloqueados.
5. **Cobertura de CI fragmentada:** existem 218 arquivos de teste Python, mas a matriz principal lista 92. Há workflows especializados adicionais, porém não foi encontrada uma garantia única que descubra e execute automaticamente todos os testes versionados.
6. **Causa-raiz do runner não comprovada:** a issue #167 continua aberta. As configurações atuais de concorrência podem explicar cancelamentos de runs antigas, mas não explicam, por si só, o desaparecimento de arquivos `set_output_*`.

**Conclusão:** antes de adicionar novas camadas de agentes, voz ou autonomia, a prioridade técnica deve ser tornar o caminho de inicialização do Core verificável, alinhar o manifesto à realidade, declarar dependências/configuração e melhorar a evidência da CI.

## 2. Método e limites

A árvore Git da `main` foi obtida de forma recursiva e não veio truncada. Foram examinados os pontos de entrada, cadeia conversacional, API, frontend, adaptadores, arquivos de configuração, unidades systemd, documentação técnica, matriz de testes e workflows relevantes.

Esta é uma **auditoria estática do inventário completo e uma inspeção aprofundada dos caminhos principais**, não uma execução local de todos os módulos. Não houve acesso ao checkout, ambiente virtual, arquivo `~/.config/nyxal/nyxal.env`, processos systemd ou filesystem do self-hosted runner. Portanto:

- não afirmo ter executado a aplicação ou as 218 suítes;
- não afirmo quais segredos ou variáveis existem na máquina do operador;
- imports condicionais são classificados como risco estático quando não foram reproduzidos em runtime;
- não é possível atribuir autoria de arquivos ao GPT somente pela árvore Git;
- causas do runner que dependem de processos, permissões, timers e logs do host permanecem pendentes de evidência local.

## 3. Inventário e organização

Na revisão da árvore da `main` foram contabilizados:

| Item | Quantidade |
|---|---:|
| Arquivos versionados | 602 |
| Arquivos Python | 400 |
| Arquivos Python com nome de teste (`teste_*.py` / `test_*.py`) | 218 |
| Arquivos Python na raiz | 383 |
| Arquivos Markdown | 119 |
| Workflows YAML em `.github/workflows` | 24 |

A maior concentração do projeto continua na raiz: **383 dos 400 arquivos Python** estão fora de pacotes/diretórios. Isso facilita imports simples, mas torna mais difícil identificar fronteiras entre produto ativo, ferramentas internas, protótipos, snapshots de etapas e testes.

### Mapa funcional

| Área | Localização | Responsabilidade observada |
|---|---|---|
| Interface | `interface/index.html`, `interface/js/` | Dashboard web consolidado; cliente HTTP e console de voz |
| API/backend | `nyxal_web_api.py` | Servidor HTTP local, rotas de chat, status, voz e integrações |
| Core conversacional | `nixal_nucleo_conversacional.py`, `nixal_dialogo_qwen.py`, `nixal_agente_qwen.py` | Orquestração conversacional, inferência e capacidades |
| Hub/roteamento | `nixal_agent_hub.py`, `nixal_intent_router.py`, `nixal_responses_api.py` | Identidade, rota conversacional e adaptadores de provedor |
| Runtime residente | `nixal_runtime.py`, `executar_nyxos_residente.py` | Ciclo residente, observabilidade, aprendizagem e experimentos governados |
| Memória/Crystal/Delta | módulos `nixal_memoria_*`, `gerenciador_cristal.py`, `nixal_delta.py`, `memoria/` | Persistência conversacional, investigação, conhecimento e estado cristalizado |
| Voz | `deploy/voice/`, adaptadores e rotas em `nyxal_web_api.py` | Protótipo de áudio local, STT/TTS, prosódia e pipeline Pipecat |
| Visão/imagem | `nixal_capacidade_visual.py` | Geração e edição de imagens com provedor visual |
| Implantação | `deploy/systemd/`, `deploy/ci/`, `deploy/ops/`, `deploy/amd_cloud/` | Serviços, instaladores, diagnósticos e integrações operacionais |
| Skills | `skills/` | Playbooks especializados versionados |
| Documentação | `docs/`, arquivos Markdown da raiz | Arquitetura, operação, decisões e relatórios históricos |

A consolidação da interface em `interface/index.html` reduziu a dispersão do frontend. O backend, porém, ainda depende de muitos módulos Python de raiz; uma migração para pacote deve ser gradual e acompanhada por testes de import/compatibilidade.

## 4. Achados técnicos

### P1 — Preflight do Ollama não garante que o Core possa ser importado

**Arquivos:** `executar_nyxal.sh`, `nixal_nucleo_conversacional.py`, `nixal_composicao_56_3_9.py`, `nixal_dialogo_qwen.py`, `nixal_ollama_http.py`.

- `EXECUCAO_LOCAL.md` diz que a aplicação usa um adaptador HTTP nativo e não exige o pacote Python `ollama`.
- `executar_nyxal.sh` aceita tanto `import ollama` quanto o fallback `import nixal_ollama_http`.
- O núcleo importa `CompositorNixal` de `nixal_composicao_56_3_9.py) no topo do módulo.
- Esse compositor contém `import ollama` direto, sem fallback para `nixal_ollama_http`.
- O diálogo Qwen, por outro lado, implementa o fallback corretamente.

**Impacto:** em um ambiente virtual que tenha o adaptador HTTP e não tenha o pacote `ollama`, o preflight pode passar e a importação do Core/API pode falhar com `ModuleNotFoundError: ollama`.

**Cobertura observada:** `teste_api_chat_sem_voz.py` injeta um módulo falso `ollama` em `sys.modules` antes de importar a API. Isso permite testar a ausência de Whisper/Kokoro, mas mascara a condição de ausência real do SDK. Não foi encontrada evidência de um teste que importe a cadeia completa em subprocesso com o pacote `ollama` deliberadamente indisponível.

**Correção recomendada:** aplicar o mesmo adaptador/fallback do diálogo ao compositor, ou remover a dependência se não for necessária; em seguida criar um teste de inicialização da API em venv limpo, sem o pacote `ollama`, usando apenas o adaptador HTTP. O preflight deve testar o mesmo conjunto de imports usado no início real da API.

### P1 — Manifesto da planta não representa a arquitetura atual

**Arquivos:** `planta_nixal/planta.json`, `leitor_planta_nixal.py), `leitor_planta_nixal_56_4_3.py), `README.md`.

O manifesto versionado declara:

- identidade `Nixal`, versão de arquitetura `56.4.2`;
- fundação ainda em construção;
- camada conversacional ainda não iniciada;
- evolução autônoma ainda não iniciada.

O README atual descreve Nível 9/10, M5.1–M5.24, LLC.1–LLC.10 e a camada conversacional contextual. O leitor da planta consome esse JSON e o usa para responder consultas de autorrepresentação.

**Impacto:** a Nyxal pode responder sobre seus próprios componentes/estado usando uma fonte que contradiz a arquitetura efetivamente publicada. Isso não é apenas documentação antiga: é um artefato de dados consultado por código.

**Correção recomendada:** definir uma única fonte de verdade arquitetural e atualizar o manifesto por uma revisão explícita, com versão, estado e inventário de componentes coerentes. Adicionar teste de consistência entre manifesto, módulos ativos e versão documentada. Não atualizar o JSON automaticamente durante import ou inicialização.

### P1 — Matriz de testes não equivale à suíte completa

**Arquivos:** `.github/matriz-validacao-raiz.txt`, `.github/workflows/nyxal-root-test-matrix.yml`, workflows especializados.

- A árvore contém 218 arquivos de teste; a matriz principal contém 92 entradas únicas.
- A própria descrição do workflow ainda diz 206 testes na raiz e 89 entradas; esses números estão desatualizados em relação à árvore/lista atuais.
- A matriz executa cada entrada isoladamente, registra resultados em `RUNNER_TEMP), isola `XDG_STATE_HOME` e tem uma guarda para não encolher abaixo de 75 entradas.
- Há workflows específicos adicionais (voz, M5, Delta, defesa, Nível 9/10, memória/LLC etc.), mas eles são acionados por eventos e filtros de caminhos diferentes.

**Impacto:** a CI tem bons gates direcionados, mas não há, na configuração analisada, uma prova única de que todo novo teste Python entre automaticamente na cobertura. Os 126 arquivos fora da matriz principal não devem ser chamados de “sem teste”: alguns são cobertos por workflows especializados; a cobertura da união de todos os workflows precisa ser inventariada.

**Correção recomendada:** gerar inventário automático dos 218 arquivos de teste, relacionar cada um a pelo menos um job/workflow e falhar quando surgir teste sem cobertura declarada. Manter exceções explícitas, justificadas e revisadas. Atualizar os comentários de contagem do workflow.

### P1 — Issue #167: cancelamentos e arquivos temporários são sintomas diferentes

**Arquivos:** `deploy/ci/diagnosticar_runner_nyxal.sh`, workflows em `.github/workflows/`, [issue #167](https://github.com/Mykkezin/Nyxal/issues/167).

A issue relata, em execuções históricas, um arquivo `_runner_file_commands/set_output_*` ausente, runs canceladas e `BlobNotFound` na coleta de logs. Continua aberta. A `main` já contém um diagnóstico somente leitura que mede permissões/diretórios, espaço/inodes, processos Runner.Listener/Worker, unidades systemd, timers e contagens de padrões nos logs.

Na configuração atual foi observado:

- a matriz principal usa `cancel-in-progress: true`, agrupada por workflow e branch/ref;
- o workflow de segurança também usa concorrência cancelável;
- o workflow de storage mantém política distinta;
- os workflows de validação não rodam necessariamente todos a cada push.

**Interpretação:** concorrência cancelável pode explicar uma run antiga marcada como cancelada quando outra run do mesmo grupo é disparada. Isso não prova nem explica o desaparecimento de `set_output_*`. `BlobNotFound` na coleta de logs também não prova, isoladamente, que um processo local apagou arquivos do runner.

**O que falta para causa-raiz:** saída do script `deploy/ci/diagnosticar_runner_nyxal.sh` executado no host; journal do serviço no mesmo intervalo UTC do erro; contagem de Runner.Listener/Worker por diretório raiz; permissões e timestamps de `_work/_temp/_runner_file_commands`; auditoria de timers/limpadores externos. A ausência do diretório depois que o job termina pode ser normal, como o próprio script alerta.

**Não recomendado:** culpar billing/quota sem evidência, desabilitar testes, ignorar checks ou declarar resolvida a issue apenas porque os três workflows baselines mais recentes passaram.

### P2 — Configuração e dependências não têm um contrato central

**Arquivos:** `EXECUCAO_LOCAL.md`, `.gitignore`, `deploy/systemd/`, arquivos `requirements-*.txt`.

Não foi encontrado na raiz `requirements.txt`, `pyproject.toml`, `setup.py`, `Pipfile` ou lockfile. As declarações de dependências localizadas são específicas para recursos opcionais:

- `deploy/voice/requirements-pipecat.txt`;
- `deploy/agent/requirements-gmail.txt`;
- `deploy/agent/requirements-mcp.txt).

O único exemplo de ambiente encontrado é `deploy/systemd/nyxal-amd-cloud.env.example`, que cobre somente o backend AMD Cloud. `.gitignore` protege `.env`, `.env.*` e ambientes virtuais, mas não existe um catálogo central dos nomes, defaults, recursos dependentes e obrigatoriedade das variáveis.

Variáveis importantes que aparecem nos caminhos centrais incluem:

- API/segurança: `NYXAL_API_HOST`, `NYXAL_API_PORT`, `NYXAL_API_TOKEN`, `NYXAL_API_BEHIND_PROXY`, `NYXAL_API_CORS_ORIGINS` (e legado singular), `NYXAL_STATE_DIR`;
- inferência local: `OLLAMA_HOST`, `NYXAL_CONVERSATIONAL_MODEL`, `NYXAL_LLM_PROVIDER`;
- persistência: `NYXAL_CONVERSATION_MEMORY_PATH`, `NYXAL_USER_DATA_DIR`;
- ferramentas: `NYXAL_FUNCTION_CALLING_ENABLED`, `NYXAL_ENABLE_PRIVATE_READ_TOOLS`, `NYXAL_ENABLE_MUTABLE_TOOLS`, `NYXAL_ENABLE_WORKSPACE_WRITE`;
- voz: `NYXAL_KOKORO_VOICE`, `NYXAL_KOKORO_SPEED`, `NYXAL_WHISPER_MODEL`, `NYXAL_TTS_MODEL`.

A documentação fala em Python 3.10 ou superior, enquanto workflows principais validam Python 3.12. Isso não prova incompatibilidade com 3.10/3.11; significa que essas versões não estão demonstradas pela CI revisada.

**Correção recomendada:** criar um arquivo central de referência de configuração (com defaults seguros, recursos opcionais, origem de cada variável e validação), um exemplo `nyxal.env.example` sem segredos e um contrato claro de ambiente Python para aplicação base e extras opcionais. Não incluir valores reais de tokens.

### P2 — Documentação contradiz o roteamento conversacional implementado

**Arquivos:** `EXECUCAO_LOCAL.md`, `docs/ROTEAMENTO_PROVEDORES_NYXAL.md`, `nixal_agent_hub.py`, `teste_nixal_agent_hub.py`, `docs/NYXAL_AGENT_STACK.md`.

`EXECUCAO_LOCAL.md` descreve chamadas a `POST /api/chat` com `provedor=openai` ou `provedor=grok`. Já o documento de roteamento declara chat local-only; o teste do hub verifica que o chat público força `provedor = "nyxal"`, inclusive quando o cliente pede outro provedor, e que Gemini/Hermes/Letta/OpenAI/Grok permanecem desativados como respondentes na configuração atual. Os documentos do Agent Stack ainda descrevem Hermes, Gemini e Letta como opções conversacionais.

A geração/edição visual Gemini é um caminho separado. O adaptador `NYXAL_LLM_PROVIDER=amd_cloud` também é um backend de inferência configurável distinto do hub de agentes.

**Correção recomendada:** documentar separadamente: (a) provedor efetivo do chat padrão; (b) backend local/AMD do diálogo; (c) adaptadores que existem no código mas estão bloqueados/desativados no produto; (d) geração de imagens. Atualizar exemplos de API para não prometer uma rota que os testes exigem manter bloqueada.

### P2 — Caminhos systemd não estão uniformes

**Arquivos:** `deploy/systemd/nyxal-api.service`, `nyxos-residente.service`, `nyxal-voice.service`, `instalar_nyxos_servicos.sh`.

Os serviços principais assumem checkout em `%h/Nyxal` e ambiente `%h/Nyxal/.venv`. O instalador também exige o caminho canônico `$HOME/Nyxal`. Já a unidade Pipecat `nyxal-voice.service` aponta para `%h/Nyxal-voz` e para um virtualenv em `~/.local/share/nyxal-voice-pipecat/venv`; há ainda um perfil de API de voz isolada com outro caminho/venv e `env -i`.

Isso é compatível com perfis experimentais separados, mas não é um único caminho de instalação reproduzível. A unidade de voz não é instalada/habilitada pelo instalador principal.

**Correção recomendada:** documentar claramente os perfis e seus diretórios, tornar caminhos configuráveis quando apropriado e fazer preflight que confira checkout, Python, dependências, endpoint API e dispositivo de áudio antes de iniciar qualquer serviço.

### P2 — Arquivos históricos e nomes que se sobrepõem exigem reconciliação

Foram encontrados nomes de versões e snapshots como `nixal_composicao.py`, `nixal_composicao_56_3_8.py`, `nixal_composicao_56_3_9.py`, módulos `nixal_runtime_antes_*` e `nixal_runtime_*_estavel.py), além de leitores da planta com e sem sufixo de microetapa.

No caminho conversacional atual, `nixal_nucleo_conversacional.py` importa `nixal_composicao_56_3_9.py`. Outros nomes permanecem em manifesto, testes, documentos ou snapshots de tarefas. Portanto, não é seguro classificá-los em bloco como código morto.

Também há dois módulos com nomes quase invertidos: `nixal_plano_central_controle.py` e `nixal_plano_controle_central.py`. A unidade residente usa o primeiro; os dois têm responsabilidades e superfícies diferentes e não são cópias byte a byte.

**Duplicidade exata confirmada:** os blobs de `experimentos/cristal_nyxal_expansivel.bin` e `experimentos/cristal_nyxal_expansivel_v2.bin` possuem o mesmo SHA de Git. São arquivos binários idênticos na árvore atual.

**Autoria:** não existe evidência no snapshot que permita dizer quais arquivos foram “criados pelo GPT”. O que pode ser afirmado com segurança é igualdade de conteúdo, sobreposição de nome/responsabilidade ou retenção histórica; atribuição de autoria exigiria revisar histórico e origem de cada commit.

**Correção recomendada:** gerar grafo de imports e referências (incluindo imports dinâmicos, manifesto, scripts e workflows), classificar cada arquivo como ativo, teste, dado-base, protótipo ou histórico e só então propor arquivamento. Preservar snapshots usados para migração.

### P2 — Voz e visão não devem ser declaradas prontas só por existirem módulos

- A unidade Pipecat é opcional e aponta para checkout separado; o README declara captura contínua e wake desativados por padrão. A PR #252 acrescentou identidade/perfil de fala e Modo Cena, mas não substitui validação física do pipeline.
- O relatório local de voz de 2026-11-06 é histórico: registrou captura/STT/TTS isolados, mas API indisponível na tentativa end-to-end daquele dia e serviço não instalado/ativado. Ele não atesta o estado atual do host.
- `nixal_capacidade_visual.py` implementa geração/edição de imagens com referência; isso não equivale a percepção de câmera, interpretação contínua de cenas ou integração de visão na sessão de voz. Na rota atual revisada não foi localizada prova de pipeline completo de percepção visual.

**Correção recomendada:** aceitar voz e visão por critérios end-to-end separados: sessão compartilhada, latência medida, cancelamento/interrupção, evidência da imagem/frame percebido, permissões e teste real no hardware de destino.

## 5. O que está validado na CI atual

No commit-base `a8d9d64ea2169ffba8ecd901bc92325b84bc07eb`, os três workflows baselines mais recentes consultados estavam concluídos com sucesso em 2026-11-14:

- [Nyxal Root Test Matrix — run 43565152761](https://github.com/Mykkezin/Nyxal/actions/runs/43565152761);
- [Nyxal API Security Baseline — run 43565152755](https://github.com/Mykkezin/Nyxal/actions/runs/43565152755);
- [Nyxal Storage and Startup Baseline — run 43565152877](https://github.com/Mykkezin/Nyxal/actions/runs/43565152877).

Isso é um sinal positivo para os testes cobertos por esses jobs. Não prova inicialização num venv limpo sem o SDK Ollama, validação de todas as 218 suítes, operação física de voz/visão ou estabilidade do runner em todas as configurações.

## 6. Pontos fortes que devem ser preservados

- API configurada para loopback por padrão; documentação proíbe exposição HTTP direta à Internet.
- Controles de CORS, autenticação Bearer no modo proxy e hardening parcial de systemd.
- Persistência de conversa e estado operacional com caminhos configuráveis e isolamento por diretório.
- Fila de tarefas com snapshot legado explicitamente migrado para armazenamento privado; o arquivo versionado não deve ser apagado sem preservar o fluxo de migração.
- Separação conceitual entre proposta, autorização, executor e evidência; a evolução automática não implica permissão automática de integração.
- Pipeline de voz experimental separado do ambiente principal, com instalação opt-in.
- Workflows de segurança, storage/startup e teste raiz distintos, cada qual cobrindo uma parte do sistema.

## 7. Plano recomendado de correção

| Ordem | Ação | Critério de aceite |
|---|---|---|
| P0 | Corrigir dependência direta `ollama` no compositor ativo ou remover a dependência | API importa e inicia em venv limpo com adaptador HTTP e sem SDK Ollama; teste reproduz esse ambiente |
| P0 | Sincronizar `planta_nixal/planta.json` com arquitetura atual | Teste valida versão, componentes e estado contra módulos ativos |
| P1 | Criar inventário de testes e cobertura por workflow | Todo teste está listado, coberto ou explicitamente excluído com motivo |
| P1 | Executar diagnóstico somente leitura do runner e anexar evidência à #167 | Processos, diretórios, permissões, timers e journal correlacionados por timestamp |
| P1 | Centralizar contrato de dependências e variáveis de ambiente | Setup base e extras opcionais reproduzíveis; exemplo sem segredos |
| P1 | Corrigir documentação de provedores e perfis systemd | API, roteador, README, guias e serviços descrevem o mesmo comportamento |
| P2 | Construir grafo de imports/referências e classificar versões históricas | Nenhum arquivo removido sem prova de não uso e plano de migração |
| P2 | Aceitar voz/visão por testes end-to-end no hardware real | Sessão compartilhada, latência, interrupção, contexto visual e rollback verificados |

## 8. Veredito

A `main` tem uma fundação de runtime e governança considerável, e os três workflows baselines recentes estão verdes. Ainda assim, há lacunas na reprodutibilidade do ambiente, na fonte de verdade arquitetural e na cobertura integral da cadeia de inicialização.

**Não recomendo ampliar agora o número de agentes ou serviços residentes.** A sequência mais segura é: corrigir o contrato de import/dependências; alinhar o manifesto; tornar a matriz de testes abrangente e a instalação reproduzível; fechar a evidência do runner; só então avançar na integração operacional de voz e percepção visual.

---

**Status desta entrega:** relatório estático baseado na `main`; nenhum arquivo de código, dado operacional, serviço ou workflow foi modificado. A PR contém somente este `AUDIT.md` e não deve ser mesclada sem revisão.
