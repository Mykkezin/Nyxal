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
- Voz automática permanece desabilitada.
- Execução física automática permanece desabilitada.
- Proposta, candidato ou resultado experimental não equivale a autorização de integração.

## Estado consolidado

A sequência Nível 9 / Nível 10 foi concluída e integrada em `main`, com regressão final validada.

Estado atual:

- Nível 9 — evolução controlada: concluído.
- Nível 10 — ciclo local formal: concluído.
- 56.5.5 — conversa contextual: integrado.
- 56.5.6 — voz contínua: integrado.
- M5.1 → M5.15 — habitat, residência, atuação supervisionada, fisiologia, controle e presença: concluídos/validados.
- M5.16 — Host Controlled Adapter: concluído/validado.
- M5.17 — Reversible Physical Sandbox: concluído/validado.
- M5.18 — Actuation Audit: concluído/validado.
- M5.19 — Resident Integration: concluído/validado.
- M5.20 — E2E: concluído/validado.
- M5.21 — AudioNyxOS: concluído/validado.
- M5.22 — Voice NyxOS: concluído/validado; voz automática permanece desabilitada.
- M5.23 — adaptadores STT/TTS: integrado em `main`; STT usa faster-whisper e TTS usa Kokoro.
- M5.24 — voz supervisionada: integrado em `main`; ciclo explícito STT → TTS validado por teste determinístico.
- AE1 → AE5 — evolução governada implementada/validada.
- LLC.1 → LLC.10 — cadeia de Learning Loop registrada e validada conforme os gates correspondentes.

## M5.23 — adaptadores de voz

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

## M5.24 — voz supervisionada

O M5.24 fechou a fronteira operacional entre `VozNyxOS` e os adaptadores STT/TTS por uma operação explicitamente solicitada.

Implementação:

- `VozNyxOS.executar_supervisionado(arquivo_audio)`;
- entrada: arquivo de áudio já disponível;
- caminho: STT explícito → texto → TTS explícito → arquivo de áudio;
- resultado estruturado e registrado;
- falha de STT interrompe o ciclo;
- ausência de TTS impede conclusão;
- entrada vazia é rejeitada.

Governança preservada:

- `voz_habilitada=False`;
- `execucao_automatica=False`;
- `execucao_fisica=False`;
- nenhum caminho de captura contínua;
- nenhum wake word;
- nenhuma reprodução física automática;
- nenhuma autoridade adicional ao gateway;
- nenhum conhecimento permanente;
- nenhuma alteração arquitetural fora do escopo.

Validação:

- teste `teste_m5_24_voz_supervisionada.py`: validado no CI;
- regressão M5/LLC/Nível 9/10: validada;
- PR #37: mergeado;
- merge commit: `a5d6b12834af728c81917e7080abbc092d1e561c`;
- HEAD do PR #37: 14/14 checks concluídos com sucesso antes do merge.

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
- observações acumuladas: **3**;
- observações bem-sucedidas: **3**;
- janela aplicada: **20 ciclos**;
- maturidade pela política: **atingida** (3/3 observações, 3/3 sucessos; mínimo 3/2);
- solicitações N9 correspondentes: **0**;
- autorização explícita: **false**;
- integração executada: **false**;
- alteração de stable/main: **false**;
- alteração de arquitetura: **false**;
- conhecimento permanente: **false**.

Conclusão: o gate de evidência empírica da AE5 está **fechado para este checkpoint**. Isso não concede autorização de integração, não cria solicitação N9 e não implica criação de AE6.

## LLC — Learning Loop Causal

A documentação atual do repositório registra a cadeia LLC.1 → LLC.10:

1. LLC.1 — influência decisória;
2. LLC.2 — feedback operacional;
3. LLC.3 — evidência causal controlada;
4. LLC.4 — evidência ambiental observacional;
5. LLC.5 — evidência causal longitudinal;
6. LLC.6 — integridade de proveniência;
7. LLC.7 — replicação distinta verificável;
8. LLC.8 — limite de escopo;
9. LLC.9 — aprendizado auditável;
10. LLC.10 — fechamento do loop.

A cadeia não concede, por si só:

- alteração de stable;
- integração em `main`;
- treinamento automático;
- autoalteração arquitetural;
- implantação automática;
- causalidade universal.

## Governança pós-M5.24

O estado atual é de **capacidade de voz supervisionada integrada**, sem voz automática.

Arquitetura de voz:

```
AudioNyxOS
→ VozNyxOS
→ Adaptador STT/TTS
→ dependência externa
```

Ciclo supervisionado:

```
arquivo de áudio existente
→ STT explícito
→ texto
→ TTS explícito
→ arquivo de áudio
→ registro auditável
```

O gateway de atuação continua reservado a ações planejadas e governadas. STT/TTS permanecem nas bordas da interface.

## Próximo marco

M5.24 está concluído. O próximo marco **não é criado automaticamente**.

Antes de qualquer nova implementação deverá ocorrer uma revisão arquitetural pós-M5.24 contendo:

1. estado real do Runtime;
2. estado real do Habitat;
3. estado real da cadeia LLC;
4. evidências operacionais novas;
5. lacunas de integração;
6. objetivo mensurável do próximo marco;
7. autoridade permitida e proibida;
8. reversibilidade;
9. validação independente;
10. critérios de promoção e rollback.

Nenhum M6 ou AE6 é criado automaticamente por este checkpoint.
