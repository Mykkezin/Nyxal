# CHECKPOINT ARQUITETURAL NYXOS — M5.22

Data: 2026-10-06

## 1. Finalidade

Este documento registra o estado arquitetural consolidado do NyxOS após a validação do M5.22.

Ele não substitui nem altera a ordem oficial de engenharia, a planta autoritativa, as regras de governança ou os documentos históricos das etapas anteriores.

## 2. Base arquitetural

A sequência oficial M5.8 → M5.15 permanece encerrada conforme `ORDEM_ENGENHARIA_NYXOS.md`.

Os marcos M5.16 → M5.22 representam extensões posteriores desenvolvidas e validadas após o encerramento dessa sequência.

Nenhum M6 é criado automaticamente por este checkpoint.

## 3. Estado consolidado

M5.8 → M5.15:
- concluídos e validados conforme a ordem oficial.

M5.16:
- adaptador controlado do host;
- leitura controlada;
- nenhuma mutação arbitrária do host.

M5.17:
- sandbox físico reversível;
- primeira mutação física confinada;
- rollback validado;
- autorização explícita obrigatória.

M5.18:
- auditoria encadeada das atuações;
- integridade dos eventos validada;
- autorização e rollback registrados.

M5.19:
- integração residente da cadeia de atuação;
- gateway preparado;
- execução física permanece desabilitada por padrão.

M5.20:
- validação E2E da cadeia percepção → fisiologia → plano → gateway;
- autorização explícita;
- mutação confinada;
- rollback;
- auditoria;
- residente não concede autorização automática.

M5.21:
- fronteira de áudio NyxOS validada;
- entrada e saída de áudio observadas;
- voz automática permanece desabilitada.

M5.22:
- interfaces STT e TTS validadas;
- interface física de áudio explicitamente validada;
- saída A2DP/SBC validada fisicamente;
- HFP/mSBC e captura de microfone permanecem dependentes de validação física específica;
- voz automática permanece desabilitada.

## 4. Governança

Permanecem válidas as seguintes restrições:

- nenhuma execução arbitrária de shell;
- nenhuma autorização implícita;
- nenhuma atuação física automática;
- nenhuma alteração arquitetural automática;
- nenhuma promoção automática de conhecimento;
- nenhuma autoridade de evolução concedida ao Habitat;
- N9 permanece como camada de autorização de integração;
- N10 permanece como validação/observabilidade;
- AE1 → AE5 permanecem como camadas governadas e separadas;
- nenhuma AE6 é criada por este checkpoint.

## 5. Estado do Delta e aprendizagem

A cadeia LLC permanece concluída e governada.

O Delta registra mudanças e evidências, mas não recebe autoridade para alterar automaticamente arquitetura, governança ou `main`.

AE1 → AE5 permanecem paralelas ao Habitat e à camada de atuação.

Nenhuma evidência deste checkpoint constitui, por si só, autorização de evolução autônoma.

## 6. Estado operacional

O estado operacional local do Habitat/Residente não faz parte deste checkpoint.

Arquivos de runtime, fisiologia, presença, gateway, auditoria e demais estados locais permanecem fora do registro arquitetural.

Não devem ser adicionados ao commit deste checkpoint.

## 7. Estado Git de referência

HEAD de referência:
`ec4924e`

origin/main de referência:
`bafd7b4`

O checkpoint é documental e não representa, por si só, uma operação de merge, reset, limpeza ou sincronização de branches.

## 8. Próxima decisão

O próximo avanço do NyxOS deverá ser definido por planejamento explícito.

Nenhum novo marco é inferido automaticamente a partir da conclusão do M5.22.

Qualquer nova etapa deverá possuir:
- objetivo explícito;
- escopo definido;
- contrato;
- critérios de validação;
- limites de autoridade;
- reversibilidade quando houver atuação;
- registro documental;
- validação independente antes de integração.

## 9. Encerramento

Este checkpoint registra o estado arquitetural conhecido em 2026-10-06.

Ele não declara consciência, autonomia irrestrita ou autoridade própria da Nyxal.

O sistema permanece sob governança explícita, com separação entre observação, decisão, capacidade, autorização, execução, auditoria e evolução.
