# Nyxal — Protocolo de Desenvolvimento

## Objetivo

Estabelecer um ciclo versionado para desenvolvimento supervisionado da Nyxal:

1. Planejamento da alteração.
2. Registro da ordem no repositório.
3. Aplicação local pela Nyxal.
4. Execução de testes.
5. Registro do resultado.
6. Checkpoint Git.
7. Sincronização com a branch de desenvolvimento.
8. Promoção para `main` somente após validação.

## Papéis

- **ChatGPT:** supervisor/arquitetura, análise, planejamento e revisão das mudanças.
- **Nyxal local:** executor, verificador e registrador dos resultados.
- **Qwen:** camada de decisão temporária, utilizada apenas onde a arquitetura atual ainda depende dela.
- **GitHub:** ponte versionada e histórico de desenvolvimento.
- **MCP:** interface operacional local da Nyxal.

## Branches

- `main`: estado estável.
- `desenvolvimento/mcp-bridge`: trabalho de integração e automação.

## Regras de segurança

- Não modificar `main` diretamente durante desenvolvimento.
- Preferir alterações pequenas e reversíveis.
- Executar testes antes de criar checkpoint.
- Não gravar segredos, tokens ou chaves no repositório.
- Não promover conhecimento permanente apenas por alteração automática.
- Não executar autoalteração fora das permissões e ferramentas explicitamente definidas.
- Toda mudança automática deve deixar rastros verificáveis: arquivo alterado, teste executado e commit correspondente.

## Estado consolidado

A sequência Nível 9 / Nível 10 foi concluída e integrada em `main`, com regressão final validada.

Estado atual:

- Nível 9 — evolução controlada: concluído.
- Nível 10 — ciclo local formal: concluído.
- 56.5.5 — conversa contextual: integrado.
- 56.5.6 — voz contínua: integrado.
- M5 — Habitat NyxOS: iniciado.
- M5.1 — observabilidade real do host: implementado e validado.
- M5.2 — processos como entidades do habitat: implementado e validado pelo CI.
- M5.3 — persistência operacional: implementada e validada pelo CI.
- M5.4 — eventos Delta de primeira classe: implementados e validados pelo CI.
- M5.5 — interface orientada ao estado real: implementada e validada pelo CI.
- M5.6 — ferramentas e módulos como recursos do habitat: implementados e validados pelo CI.
- M5.7 — ciclo operacional residente: implementado e validado pelo CI.
- AE1 — descoberta de auto-evolução governada: implementada e validada pelo CI.
- AE2 — experimento isolado automático sob política: implementado e validado pelo CI.
- AE3 — comparação e aprendizagem automática: implementada e validada pelo CI.
- AE4 — ciclo residente de evolução: implementado e validado pelo CI.
- AE5 — descoberta contínua com governança: implementada e validada pelo CI.

## Gate M5 / AE5 — estado consolidado

O gate desta fase foi revalidado após o endurecimento da AE5.1.0.

- reconciliação histórica AE4 → AE5: validada;
- janela móvel de 20 ciclos: validada;
- deduplicação por ciclo: validada;
- formalização persistente: validada;
- reconciliação histórica idempotente: validada;
- invariantes de autorização e integração: preservados;
- CI M5/AE1–AE5: **SUCCESS**;
- CI Nível 9/10 determinístico: **SUCCESS**;
- main: não modificada.

Não há promoção automática para AE6 neste checkpoint. O próximo passo arquitetural é
a revisão das evidências acumuladas pela AE5 e a definição supervisionada do próximo
marco somente depois dessa revisão.

## Gate AE5 — revisão de evidências acumuladas

Este gate separa validação estrutural de evidência empírica. A existência de testes, persistência e integração no ciclo residente comprova o comportamento implementado, mas não substitui uma sequência real de observações acumuladas.

### Evidência já validada

- integração AE1 → AE4 → AE5 no ciclo residente: validada por regressão;
- persistência e reconciliação histórica: validadas;
- janela móvel de 20 ciclos: validada;
- deduplicação e idempotência: validadas;
- classificação de maturidade: validada por testes determinísticos;
- invariantes de autorização, integração, alteração de arquitetura e conhecimento permanente: preservadas;
- CI M5/AE1–AE5: **SUCCESS**.

### Evidência ainda não comprovada no início do gate

Antes da observação operacional, ainda não estavam comprovados:

- existência de uma série histórica real de ciclos residentes suficiente para demonstrar maturidade operacional fora dos testes;
- recorrência de oportunidades reais em ciclos independentes;
- persistência de sinais reais atravessando a janela móvel de 20 ciclos;
- ocorrência real de uma hipótese que alcance os critérios de maturidade sem ser produzida artificialmente pelo teste;
- existência de uma solicitação N9 correspondente surgida de um fluxo operacional real.

### Resultado da revisão operacional — 2026-10-05

A execução residente real forneceu a evidência necessária para este checkpoint, sem criação de sinais artificiais:

- ciclos AE4 válidos: **3**;
- ciclos distintos observados: **3**;
- linha de evidência avaliada: **1**;
- limitação recorrente: dependencias_arquiteturais_nao_declaradas;
- hipótese recorrente: "É possível que existam dependências entre os componentes da arquitetura que ainda não estão registradas formalmente na planta.";
- observações acumuladas: **3**;
- observações bem-sucedidas: **3**;
- janela aplicada: **20 ciclos**;
- maturidade pela política: **atingida** (3/3 observações, 3/3 sucessos; mínimo 3/2);
- solicitações N9 correspondentes no diretório operacional: **0**;
- autorização explícita: **false**;
- integração executada: **false**;
- alteração de stable/main: **false**;
- alteração de arquitetura: **false**;
- conhecimento permanente: **false**.

Os ciclos observados foram:

```text
fase_01_1791181735125859641
fase_01_1791181738172345762
fase_01_1791181742859225468
```

Conclusão do checkpoint: o gate de evidência empírica da AE5 está **FECHADO PARA ESTE CHECKPOINT**, com maturidade operacional demonstrada pela política vigente. Isso não concede autorização de integração, não cria solicitação N9 e não implica criação de AE6.

### Ferramenta de auditoria

O arquivo `auditar_evidencias_ae5.py` foi adicionado como auditor somente leitura do gate. Ele inspeciona as auditorias AE4 e as oportunidades persistidas no ambiente operacional externo ao repositório, agrupa por limitação + hipótese e calcula a janela de evidência sem criar, reconciliar ou alterar registros.

Execução local:

```bash
python3 auditar_evidencias_ae5.py
```

Código de saída `0`: há evidência operacional encontrada. Código de saída `2`: nenhuma evidência operacional encontrada. Nenhum dos dois estados concede autorização ou altera `main`.

### Critério de saída

O gate permanece **ABERTO** até que exista evidência observada em execução real ou em um conjunto de ciclos operacionais explicitamente identificados como observação, sem fabricar sinais para satisfazer os critérios. Quando os critérios forem satisfeitos, o fechamento é restrito ao checkpoint observado e não concede autoridade de integração.

A revisão deve registrar, no mínimo:

1. identificadores dos ciclos observados;
2. oportunidades AE1 efetivamente observadas;
3. auditorias AE4 correspondentes;
4. sinais reconciliados pela AE5;
5. janela de evidência utilizada;
6. maturidade calculada;
7. eventual formalização N9 já existente, sem criação automática;
8. confirmação das invariantes de autorização e integração.

Com este checkpoint validado, qualquer próximo marco continua dependente de proposta supervisionada e revisão arquitetural. **Nenhuma AE6 é criada ou ativada automaticamente por este gate.**

## Checkpoint M5.8 — validação do mapa de dependências arquiteturais

Em 2026-10-05, a proposta supervisionada M5.8 foi validada por dois testes complementares:

- validação estrutural da proposta: **PASSOU**;
- cobertura automática por importações diretas entre os componentes Python declarados na planta: **PASSOU**;
- relações diretas encontradas: **4**;
- relações correspondentes declaradas na proposta: **4**;
- relações ausentes na proposta: **0**;
- relações declaradas sem evidência direta: **0**.

O critério de M5.8, portanto, está satisfeito neste checkpoint **dentro do escopo de importação direta**.

A proposta permanece não autoritativa. `planta_nixal/planta.json`, Runtime, ciclo residente e `main` não foram alterados por este marco. Nenhuma promoção de arquitetura ou integração foi executada.

## Próximo objetivo

Avançar o M5/Habitat sem criar um kernel próprio.

Primeiro ciclo:

```
host
→ observabilidade
→ processos
→ persistência operacional
→ eventos Delta
→ interface orientada a estado real
→ ciclo operacional residente
```

O primeiro marco M5.1 mantém a ponte somente leitura e não altera hardware, estado persistente ou os gates de evolução.

M5.7 conclui o Habitat NyxOS desta fase. AE1 e AE2 já estão integradas no branch de desenvolvimento:
AE1 descobre e registra oportunidades; AE2, quando explicitamente habilitada, processa no máximo uma
solicitação formal pronta por ciclo através do caminho remoto N9.

AE3 está implementada para interpretar resultados do AE2/N9, validar comparação e aprendizado
e classificar a evidência sem conceder autorização.

AE4 está implementado para orquestrar AE1→AE2→AE3 em uma única passagem residente, registrar um
resumo auditável por ciclo e preservar a ausência de causalidade implícita entre oportunidade e
solicitação quando o vínculo não estiver explicitamente persistido.

AE5 está implementada para acumular sinais repetidos da AE1/AE4, agrupar linhas de evidência,
classificar maturidade e solicitar formalização externa sem inventar objetivo, métrica, baseline
ou artefato.

O próximo passo é a definição supervisionada do próximo marco, mantendo autorização
explícita, isolamento de candidatos e reversibilidade como barreiras invariantes.


## M5.8 — proposta de mapa de dependências arquiteturais

O primeiro marco supervisionado após o fechamento do gate AE5 é a formalização de um mapa **não autoritativo** das dependências entre componentes já declarados na planta.

Critério da proposta atual:

- declarar somente relações cuja evidência direta foi observada no código, começando por importações entre componentes da planta;
- não inferir dependências de dados, runtime, persistência ou temporalidade sem evidência específica;
- não alterar `planta_nixal/planta.json`;
- não alterar o Runtime nem o ciclo residente;
- manter os gates de evolução e integração intactos.

Artefatos:

- `M5_8_DEPENDENCIAS_ARQUITETURAIS.md`;
- `m5_8_dependencias_arquiteturais_proposta.json`;
- `teste_m5_8_dependencias_arquiteturais.py`.

A proposta identifica, neste checkpoint, as relações:

```
agente_qwen        → capacidades
composicao        → agente_qwen
executor_contexto → operacoes_contexto
interpretacao_qwen → gerenciador_cristal
```

Este marco não fecha a arquitetura como fato definitivo. A próxima decisão é revisar o mapa proposto antes de qualquer atualização da planta autoritativa. Nenhuma AE6 é criada por M5.8.
