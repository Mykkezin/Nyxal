# Nyxal local

## O que está conectado

A interface web existente é servida pela própria API local. O caminho textual usa `NucleoConversacionalNixal`, `DialogoQwenNixal`, o agente de capacidades e a memória `MemoriaConversacionalNixal`. A memória de conversas é salva em `~/.local/share/nyxal/conversas.json`, com permissões privadas e bloqueio entre processos. Defina `NYXAL_CONVERSATION_MEMORY_PATH` para usar outro arquivo (em testes, prefira um caminho temporário).

O respondente local é Ollama e usa `NYXAL_CONVERSATIONAL_MODEL` (padrão atual `qwen2:7b`). OpenAI e xAI podem ser selecionados explicitamente via campo `provedor` na API, desde que chave e modelo estejam configurados. Não há fallback silencioso entre modelos em uma solicitação explícita.

## Dependências e início

Use Python 3.10 ou posterior. A Nyxal usa seu adaptador HTTP nativo para Ollama e não exige o pacote Python `ollama`. Instale e inicie Ollama separadamente; a Nyxal só consulta a API e não instala serviços.

```bash
export NYXAL_CONVERSATIONAL_MODEL=qwen2:7b
./executar_nyxal.sh
```

Abra <http://127.0.0.1:8010/>. A API também responde em <http://127.0.0.1:8010/health>. O script verifica as dependências e a disponibilidade do Ollama, limita o host a loopback e não altera serviços do sistema. Ctrl+C encerra a API e seus serviços auxiliares iniciados por ela.

## Provedores externos

Para usar OpenAI, defina `NYXAL_OPENAI_API_KEY` (ou `OPENAI_API_KEY`) e `NYXAL_OPENAI_MODEL`. Para xAI, use `NYXAL_GROK_API_KEY` (ou `XAI_API_KEY`) e `NYXAL_GROK_MODEL`. As URLs padrão são as oficiais; o adaptador recusa hosts alternativos e redirecionamentos. A API não envia chave para a interface.

Uma solicitação pode selecionar `openai` ou `grok` com `POST /api/chat`, usando JSON como `{"mensagem":"Olá","provedor":"openai"}`. Sem provedor no payload, o diálogo local configurado continua sendo usado. A API retorna `provedor` e `modelo` efetivos quando o adaptador os informa.

## Agente, contexto e ferramentas

O núcleo atual tem um único diálogo conversacional com encaminhamento determinístico às capacidades já registradas. Ele ainda não implementa um registro de agentes Nyxal selecionáveis; portanto, Capitu, Dumont, Jaci, Caapora e Anhangá não são apresentados como agentes operacionais nesta etapa. O uso local de ferramentas depende do modelo e das regras governadas existentes. O caminho externo OpenAI/xAI está habilitado para conversa textual e não executa ferramentas. Perfis Arandu independentes ainda não estão conectados à interface; os nomes Arandu não representam modelos treinados.

## Diagnóstico

- `GET /health`: processo HTTP ativo.
- `GET /api/agent/contexto`: configuração resumida do hub; não retorna chaves.
- Erro `provedor_indisponivel`: confira modelo, credencial e disponibilidade do provedor.
- Erro de dependência ao iniciar: confira o Python apontado por `NYXAL_PYTHON` e a importação dos módulos do projeto.
- Para modelos locais, confirme que `OLLAMA_HOST` (padrão `http://127.0.0.1:11434`) responde e que o modelo configurado foi baixado previamente.

Não use o modo de voz como requisito do chat textual. A captura contínua de áudio não é habilitada pelo script de inicialização.
