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
- branches de desenvolvimento: alterações isoladas, pequenas e reversíveis.

## Regras de segurança

- Não modificar `main` diretamente durante desenvolvimento.
- Preferir alterações pequenas e reversíveis.
- Executar testes antes de criar checkpoint.
- Não gravar segredos, tokens ou chaves no repositório.
- Não promover conhecimento permanente apenas por alteração automática.
- Não executar autoalteração fora das permissões e ferramentas explicitamente definidas.
- Toda mudança automática deve deixar rastros verificáveis: arquivo alterado, teste executado e commit correspondente.
- Voz automática permanece desabilitada até que um marco específico seja aprovado.
- Execução física automática permanece desabilitada.
- Proposta, candidato ou resultado experimental não equivale a autorização de integração.

## Estado consolidado

A sequência Nível 9 / Nível 10 foi concluída e integrada em `main`, com regressão final validada.

Estado atual:

- Nível 9 — evolução controlada: concluído.
- Nível 10 — ciclo local formal: concluído.
- 56.5.5 — conversa contextual: integrado.
- 56.5.6 — voz contínua: integrado.
- M5 — Habitat NyxOS: sequência M5.8 → M5.15 encerrada/validada.
- M5.1 → M5.15 — habitat, residência, atuação supervisionada, fisiologia, controle e presença: concluídos/validados.
- M5.16 — Host Controlled Adapter: concluído/validado.
- M5.17 — Reversible Physical Sandbox: concluído/validado.
- M5.18 — Actuation Audit: concluído/validado.
- M5.19 — Resident Integration: concluído/validado.
- M5.20 — E2E: concluído/validado.
- M5.21 — AudioNyxOS: concluído/validado.
- M5.22 — Voice NyxOS: concluído/validado; voz automática permanece desabilitada.
- M5.23 — adaptadores STT/TTS: integrado em `main`; STT usa faster-whisper e TTS usa Kokoro.
- AE1 — descoberta de auto-evolução governada: implementada e validada.
- AE2 — experimento isolado automático sob política: implementado e validado.
- AE3 — comparação e aprendizagem automática: implementada e validada.
- AE4 — ciclo residente de evolução: implementado e validado.
- AE5 — descoberta contínua com governança: implementada e validada.

### M5.23 — adaptadores de voz

O M5.23 integrou adaptadores externos de STT/TTS sem alterar o contrato central de `VozNyxOS`.

Estado registrado:

- PR #34: mergeado.
- Merge commit: `195b1186a19e3be058b55e57c827e29461a91704`.
- STT: `faster-whisper`.
- TTS: `Kokoro`.
- Contrato: `VozNyxOS` recebe callables STT/TTS.
- Dependências externas permanecem na borda.
- Injeção de dependência permanece disponível para validação determinística.
- Voz automática: desabilitada.
- Execução física automática: desabilitada.
- Autoridade de evolução: não concedida.
- M6: não criado automaticamente.

O HEAD do PR #34 (`e8060bd01546d3117f38c24f7bd7bd5864114da7`) teve 14/14 checks do GitHub Actions concluídos com sucesso antes do merge.

O checkpoint pós-M5.23 está registrado separadamente em `CHECKPOINT_POS_M5_23.md` e permanece como registro histórico do estado integrado.

## Gate M5 / AE5 — estado consolidado

O gate desta fase foi revalidado após o endurecimento da AE5.1.0.

- reconciliação histórica AE4 → AE5: validada;
- janela móvel de 20 ciclos: validada;
- deduplicação por ciclo: validada;
- formalização persistente: validada;
- reconciliação histórica idempotente: validada;
- invariantes de autorização e integração: preservados;
- CI M5/AE1–AE5: SUCCESS;
- CI Nível 9/10 determinístico: SUCCESS.

Não há promoção automática para AE6.

## Gate AE5 — revisão de evidências acumuladas

Este gate separa validação estrutural de evidência empírica. A existência de testes, persistência e integração no ciclo residente comprova o comportamento implementado, mas não substitui uma sequência real de observações acumuladas.

### Evidência validada

- integração AE1 → AE4 → AE5 no ciclo residente;
- persistência e reconciliação histórica;
- janela móvel de 20 ciclos;
- deduplicação e idempotência;
- classificação de maturidade;
- invariantes de autorização, integração, alteração de arquitetura e conhecimento permanente;
- evidência operacional real do checkpoint de 2026-10-05.

### Resultado da revisão operacional — 2026-10-05

A execução residente real forneceu a evidência necessária para o checkpoint, sem criação de sinais artificiais:

- ciclos AE4 válidos: **3**;
- ciclos distintos observados: **3**;
- linha de evidência avaliada: **1**;
- limitação recorrente: `dependencias_arquiteturais_nao_declaradas`;
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

Conclusão: o gate de evidência empírica da AE5 está **fechado para este checkpoint**, com maturidade operacional demonstrada pela política vigente. Isso não concede autorização de integração, não cria solicitação N9 e não implica criação de AE6.

## M5.8 → M5.15 — sequência encerrada

A sequência supervisionada foi concluída:

1. M5.8 — dependências arquiteturais observadas — **concluído/validado**;
2. M5.9 — residência Linux via systemd — **concluído/validado**;
3. M5.10 — gateway de atuação do host — **concluído/validado**;
4. M5.11 — controle de processos e aplicativos — **concluído/validado**;
5. M5.12 — corpo térmico e ventilação — **concluído/validado**;
6. M5.13 — fisiologia operacional — **concluído/validado**;
7. M5.14 — plano central de controle — **concluído/validado**;
8. M5.15 — presença de máquina — **concluído/validado**.

Nenhum M6 é criado automaticamente.

## LLC — Learning Loop Causal

O LLC permanece uma linha arquitetural separada da concessão de autoridade de evolução.

### LLC.1 — Influência decisória determinística

Estado: **validado no CI**.

A primeira camada prova que um sinal estruturado de aprendizado anterior pode alterar a escolha do Runtime entre alternativas previamente registradas.

A prova compara:

```
decisão_sem_aprendizado
        vs.
decisão_com_aprendizado
```

A prova é limitada à influência dentro do mecanismo de decisão. `causalidade_ambiental_comprovada` permanece false.

### LLC.2 — próximo marco da linha LLC

O objetivo conceitual é fechar o elo:

```
aprendizado anterior
→ decisão influenciada
→ ação
→ resultado observado
→ ganho/perda
→ novo aprendizado
```

LLC.2 não cria uma nova memória, novo agente ou nova autoridade de integração.

## Governança pós-M5.23

O estado atual é de **integração arquitetural com voz disponível como capacidade externa, mas sem execução automática**.

A arquitetura mantém:

```
percepção/estado
→ diagnóstico
→ necessidade
→ priorização
→ decisão
→ ação/investigação
→ resultado
→ avaliação
→ registro
→ aprendizado/memória
→ próximo ciclo
```

Para voz:

```
AudioNyxOS
→ VozNyxOS
→ Adaptador STT/TTS
→ dependência externa
```

A voz não recebe autoridade especial. O gateway de atuação continua reservado a ações planejadas e governadas; STT/TTS permanecem nas bordas da interface.

## Próximo marco

O próximo marco **não é criado automaticamente**.

Antes de qualquer implementação, deverá existir uma proposta supervisionada contendo:

1. objetivo mensurável;
2. escopo exato;
3. contrato de entrada/saída;
4. autoridade concedida e autoridade proibida;
5. reversibilidade;
6. testes determinísticos;
7. validação independente;
8. documentação;
9. critérios de promoção;
10. critérios de rollback.

A hipótese de trabalho para a próxima revisão é avaliar se **LLC.2** deve ser o próximo marco arquitetural, sem iniciar sua implementação antes da aprovação explícita do escopo.

Nenhuma AE6 é criada automaticamente e nenhum M6 é iniciado por este documento.
