# Auditoria de compatibilidade: OpenJarvis e Nyxal

## Proveniência da auditoria

- Repositório: <https://github.com/open-jarvis/OpenJarvis>
- Checkout de leitura: shallow clone em `/tmp/openjarvis-review-20261111`, fora do checkout Nyxal.
- Commit estudado: `bb5bd1aaea8c7d962c3d65f4816cfb7022cc4836` (`fix(desktop): prepare verified stable release with startup fixes (#1204)`, 2026-11-10).
- Licença no checkout: Apache License 2.0, arquivo `LICENSE`.
- `NOTICE`: não encontrado na raiz do commit auditado.
- Instalador OpenJarvis: não executado. Dependências OpenJarvis: não instaladas.
- Código OpenJarvis copiado: nenhum. Não há avisos de copyright OpenJarvis incorporados ao código Nyxal.

O checkout possui implementações sob `src/openjarvis/` e documentação de arquitetura em `docs/architecture/`. Foram examinados os contratos e implementações de `engine/_stubs.py`, `engine/ollama.py`, `engine/_discovery.py`, `intelligence/model_catalog.py`, `core/registry.py`, `agents/simple.py`, `agents/orchestrator.py`, `agents/native_react.py`, `tools/_stubs.py`, `skills/loader.py`, `mcp/`, `memory/`, `traces/`, `learning/routing/`, `evals/`, `bench/` e `server/`. A conclusão abaixo vem da leitura do código e docs nesse commit; não significa que o pacote inteiro tenha sido instalado ou executado.

O `pyproject.toml` declara como dependências base Click, croniter, datasets, ddgs, HTTPX, OpenAI SDK, NVIDIA ML bindings, PostHog, psutil, Telegram Bot, Rich, tomlkit e websockets. As extras incluem, entre outras, FastAPI/uvicorn, vLLM, LiteLLM, Torch/ColBERT, FAISS/sentence-transformers e speech. Isso reforça a escolha de não instalar o framework para obter somente o contrato do engine; a integração Ollama da Nyxal usa a biblioteca padrão.

## Mapa de compatibilidade

| Recurso OpenJarvis | Decisão | Compatibilidade com Nyxal e ação |
|---|---|---|
| Contrato `InferenceEngine`: generate, stream, list_models, health, can_serve | **ADAPTAR PARA A NYXAL** | Bom contrato para desacoplar o diálogo de um fornecedor. O adaptador `nixal_ollama_http.py` usa a API nativa Ollama e expõe geração, streaming NDJSON, catálogo e health sem depender do SDK Python. Ainda falta unificar nele os adaptadores OpenAI/xAI e converter todo o diálogo para o contrato comum. |
| `OllamaEngine` HTTP nativo e endpoint `/api/tags` | **ADAPTAR PARA A NYXAL** | Confirmou que o SDK não é necessário. A implementação Nyxal independente usa biblioteca padrão, resposta limitada a 4 MiB, timeout configurável e bloqueio de redirecionamentos. Nenhum código-fonte OpenJarvis foi copiado. |
| `ModelSpec`, `ModelRegistry`, `discover_engines/models` | **USAR COMO REFERÊNCIA ARQUITETURAL** | Registry tipado e descoberta de engine/modelo são úteis para Intelligence. Nyxal ainda precisa de catálogo/capacidades por modelo, seleção real e perfis Arandu. Não importar o grande catálogo OpenJarvis: ele lista modelos que não existem no host e pode sugerir cargas inadequadas. |
| `BaseAgent`, `AgentContext`, `AgentResult`, `AgentRegistry` | **USAR COMO REFERÊNCIA ARQUITETURAL** | Contrato de agente explícito facilita teste e registro. Nyxal já tem `NucleoConversacionalNixal`, `AgenteNixalQwen`, `NyxalAgentHub` e capacidades governadas; não adicionar uma segunda pilha de execução concorrente. |
| `SimpleAgent` | **USAR COMO REFERÊNCIA ARQUITETURAL** | Uma chamada para chat simples minimiza latência e custo; compatível com priorizar Capitu. A conversa atual deve continuar no núcleo Nyxal para preservar a memória, tools e contratos existentes. |
| `OrchestratorAgent` com `ToolUsingAgent`, `max_turns`, before-tool hook | **ADAPTAR PARA A NYXAL** | Limite de voltas e hook de governança fail-closed são princípios úteis. O agente atual de diálogo já tem function calling limitado e ferramentas governadas; qualquer extração para uma classe precisa preservar autorização explícita e auditoria. |
| `NativeReActAgent` textual | **USAR COMO REFERÊNCIA ARQUITETURAL** | Observação e ação em etapas são auditáveis, mas prompting ReAct pode revelar raciocínio privado e é menos confiável que chamadas tipadas. Nyxal deve registrar decisões resumidas, chamada, resultado e justificativa operacional, sem exibir cadeia interna. |
| `Operative` e monitores de longa duração | **NÃO UTILIZAR AGORA** | É orientado a operações persistentes/agendamento. A prioridade é responder a conversas locais; um worker residente amplia risco, consumo e superfície operacional sem requisito imediato. |
| `ToolExecutor` e base `BaseTool` | **ADAPTAR PARA A NYXAL** | Parsing de argumentos, despacho e resultados tipados são úteis. Manter `GerenciadorCapacidades`, `nixal_tool_use.py`, permissões de leitura/escrita e autorização Nyxal como autoridade. Tool call do modelo nunca é autorização. |
| Skills: manifests, carregador, permissões, fontes externas | **USAR COMO REFERÊNCIA ARQUITETURAL** | Metadados, versão, capacidades necessárias, origem e política de invocação são bons campos. Skills Nyxal atuais não devem ser interpretadas como código confiável nem instaladas automaticamente. Importação externa exige revisão de conteúdo, dependências e permissões. |
| MCP client/server/transports | **ADAPTAR PARA A NYXAL** | Nyxal já possui servidor e runtime MCP. A descoberta OpenJarvis é referência para protocolo e adaptadores, não motivo para conectar servidores externos desconhecidos ou duplicar o servidor existente. |
| `MemoryBackend`, SQLite/FTS5, BM25, dense e hybrid retrieval | **USAR COMO REFERÊNCIA ARQUITETURAL** | Separar contrato de busca e armazenamento é útil. Nyxal tem memória conversacional, conhecimento, investigação, Delta e cristal com isolamento/persistência próprios; não substituir nem migrar dados para SQLite. Avaliar retrieval lexical por interface, mantendo origem, status epistemológico e não confiabilidade explícitos. Embeddings locais existentes não são modelo de chat. |
| `MemoryService` de extração assíncrona de fatos | **NÃO UTILIZAR AGORA** | A extração automática de fatos em background conflita com a regra Nyxal de não promover conversa a conhecimento permanente. Só caberia futuramente como fila de candidatos para revisão humana e integração explícita. |
| `TraceCollector`, `TraceStore` SQLite e EventBus | **ADAPTAR PARA A NYXAL** | Capturar engine/modelo, latência, tokens, agente, ferramentas e sucesso/falha é valioso. Implementar com retenção e redação de segredos, sem persistir prompts/respostas completos por padrão nem tocar nas memórias de identidade. |
| Learning router, feedback, otimização e treino | **USAR COMO REFERÊNCIA ARQUITETURAL** | Começar observacional: comparar qualidade, latência e recursos por perfil. Não aplicar automaticamente pesos, prompts fundamentais, permissões ou memória. Treinadores/GRPO e execução de benchmarks longos não devem rodar no host durante a validação de chat. |
| Bench latency/throughput/energy e hardware discovery | **ADAPTAR PARA A NYXAL** | Inventário e métricas passivas são úteis. O host atual tem AMD Navi 33; `rocm-smi` não está instalado. Não afirmar aceleração GPU sem confirmar backend. Benchmark que carregue modelo fica bloqueado enquanto swap estiver saturada. |
| API FastAPI/StreamingResponse e interface OpenJarvis | **USAR COMO REFERÊNCIA ARQUITETURAL** | Streaming/contratos podem informar evolução da API. Nyxal possui API HTTP e interface próprias; substituir frontend ou adicionar FastAPI não é necessário para a primeira conversa integrada. |
| Pacote OpenJarvis inteiro como dependência da Nyxal | **NÃO UTILIZAR** | Puxa muitos extras opcionais (cloud SDKs, memória vetorial, web/server, desktop, mineração) e cria dois runtimes. Manter integração seletiva, sem instalação global ou dependência obrigatória. |

## Componentes Nyxal preservados

- Conversa e memória: `nixal_nucleo_conversacional.py`, `nixal_dialogo_qwen.py`, `nixal_memoria_conversacional.py`.
- Agente/capacidades/tools: `nixal_agente_qwen.py`, `nixal_capacidades.py`, `nixal_tool_use.py` e `nixal_agent_hub.py`.
- API local: `nyxal_web_api.py`; o servidor já é restrito a loopback por padrão.
- Estado epistemológico: memórias de conhecimento/investigação, Delta e cristalização não foram substituídos.

## Integração implementada nesta etapa

`nixal_ollama_http.py` fornece um cliente/engine pequeno para o Ollama HTTP nativo, com `chat`, tools, streaming NDJSON, `list_models`, `health`, timeout e erros sanitizados. `nixal_dialogo_qwen.py` e `nixal_agente_qwen.py` usam esse adaptador se o pacote Python `ollama` não estiver instalado; se o pacote existir, o comportamento legado permanece. `teste_nixal_ollama_http.py` valida os payloads e falhas com simulador. Uma consulta real não inferencial confirmou Ollama 0.34.4 e os modelos instalados.

Não houve cópia de código OpenJarvis, alteração de dependências Nyxal por OpenJarvis, importação do pacote ou instalação de componentes. Assim, não há modificações de código OpenJarvis cuja proveniência necessite cabeçalho Apache; a licença e commit de referência estão registrados acima.

## Estado do host na auditoria

- Ollama 0.34.4 responde em `127.0.0.1:11434`.
- Modelos presentes: `qwen2:7b` (Q4_0, 7.6B, 4,4 GB no disco) e `nomic-embed-text:latest` (embeddings; **não** é modelo conversacional).
- Ollama reportou `ollama ps` vazio, portanto nenhum modelo estava carregado.
- Memória medida: 15 GiB totais, 4,7 GiB disponíveis; swap 2 GiB totalmente usada.
- GPU: AMD Navi 33 / Radeon RX 7700S/7600M XT; `rocm-smi` ausente. Nenhum caminho de aceleração foi provado.
- Decisão: não iniciar inferência Qwen 7B com esse estado de memória, nem descarregar processos ou baixar modelo. Health e listagem podem ser consultados sem carregar pesos.

## Pendências

1. Fazer `nixal_ollama_http` ser a implementação única mesmo quando o SDK estiver instalado e adicionar cancelamento explícito/retry limitado.
2. Criar Intelligence Nyxal com perfis Gota/Rio/Pororoca configuráveis, capacidades obtidas do servidor e roteamento que respeite orçamento de hardware.
3. Integrar stream da engine até a interface sem quebrar contrato de sessão e memória.
4. Registrar traces operacionais com redação, retenção limitada e opt-in para conteúdo de interação.
5. Implementar seleção real de agente por request; não expor Dumont/Jaci/Caapora/Anhangá como funcionais até seus caminhos e testes existirem.
6. Validar o caminho completo do modelo real quando houver margem de memória suficiente, swap disponível ou autorização para encerrar processos concorrentes/baixar alternativa.
