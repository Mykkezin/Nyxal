# Avaliação técnica do OpenJarvis para a Nyxal

Data da avaliação: 2026-10-23

## Decisão executiva

O OpenJarvis, projeto Stanford sob licença Apache-2.0, apresenta padrões úteis para IA local: engines com interface comum, descoberta e verificação de backends, traces por execução, telemetria de latência/custo/energia, avaliação baseada em traces e memória recuperável. A Nyxal já possui runtime, memória persistente, Delta, observabilidade do host, integração Ollama/AMD, Agent Hub, laboratório remoto e ciclo de aprendizagem governado. Substituir essas camadas pelo OpenJarvis criaria duplicação e ampliaria o risco de regressão.

A estratégia é adotar padrões, não importar o framework inteiro. Esta melhoria acrescenta uma trilha HTTP estruturada ao servidor existente. Ela produz evidência operacional sobre a API sem criar uma segunda memória ou conceder capacidade de autoalteração.

## O que vale aproveitar

| Padrão observado no OpenJarvis | Aplicação recomendada à Nyxal | Decisão |
|---|---|---|
| Trace por consulta, com etapas e duração | Correlacionar requisições e falhas sem gravar conteúdo da conversa | Implementado nesta branch: metadados HTTP e X-Request-ID |
| Métricas de inferência (latência, tokens, engine) | Instrumentar adaptadores quando o backend realmente expuser esses dados | Próxima investigação; tokens/energia ainda não são prometidos |
| Descoberta e health-check de engines | Diagnóstico unificado para Ollama/local e AMD remoto preservando interfaces atuais | Proposta; requer mapear os contratos existentes |
| Avaliações reproduzíveis por traces | Converter falhas reais em regressões revisáveis | Proposta; sem aprendizado automático a partir de requests de usuários |
| Memória recuperável e contexto | Melhorar a recuperação na memória Nyxal existente | Não criar armazenamento paralelo sem auditoria da memória atual |
| Guardrails e sandbox para agentes | Reforçar fronteiras de adaptadores e experimentos | Requer revisão específica; nenhuma execução adicional foi habilitada |

## Mudança desta branch

### nixal_trilha_http.py

- Emite uma linha JSON por requisição.
- Registra timestamp UTC, ID de correlação, método, rota sem query string, status, duração e classe do resultado.
- Registra apenas o tipo de exceção, nunca a mensagem.
- Não persiste corpo, prompt, resposta, cabeçalhos, token Bearer, cookies, IP ou query strings.
- Grava fora da árvore Git por padrão em ~/.local/state/nyxal/http-traces.jsonl (ou sob XDG_STATE_HOME).
- Define permissões restritivas para diretório/arquivo recém-criados e limita o histórico com rotação.
- Pode ser desligado por NYXAL_HTTP_TRACE_ENABLED=false; caminho, tamanho e backups são configuráveis.
- Falha de telemetria não deve derrubar a API.

### Integração web

O NyxalAPIHandler gera um X-Request-ID por requisição, captura status/duração e grava a trilha. O log textual também omite query strings. O rastreamento não altera respostas de negócio nem o fluxo AE/LLC/N9/N10.

## Validação

A suíte isolada teste_nixal_trilha_http.py cobre privacidade da query string, classificação de status, exceções sem mensagens, desligamento e rotação. Execute na raiz:

    python -m unittest teste_nixal_trilha_http.py -v

É necessário também validar o workflow CI do repositório e a regressão existente antes do merge. Testes isolados não equivalem a validar a aplicação web completa.

## Fontes

- OpenJarvis README: https://github.com/open-jarvis/OpenJarvis
- Arquitetura: https://github.com/open-jarvis/OpenJarvis/blob/main/docs/architecture/overview.md
- Learning & traces: https://github.com/open-jarvis/OpenJarvis/blob/main/docs/architecture/learning.md
- Segurança: https://github.com/open-jarvis/OpenJarvis/blob/main/docs/architecture/security.md
- Memória: https://github.com/open-jarvis/OpenJarvis/blob/main/docs/architecture/memory.md
- Nyxal README: https://github.com/Mykkezin/Nyxal/blob/main/README.md
- Nyxal revisão pós-M5.24: https://github.com/Mykkezin/Nyxal/blob/main/REVISAO_ARQUITETURAL_POS_M5_24.md

O código desta melhoria foi escrito para os contratos atuais da Nyxal; não incorpora código-fonte do OpenJarvis. A referência ao projeto é de inspiração arquitetural e atribuição.
