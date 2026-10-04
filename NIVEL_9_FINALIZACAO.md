# Nível 9 — Finalização de Evolução Controlada

## Escopo fechado

O Nível 9 / M4 considera concluído o ciclo arquitetural quando existe uma cadeia verificável:

```
limitação
→ hipótese provisória
→ solicitação formal
→ artefato experimental
→ baseline
→ experimento remoto
→ resultado
→ comparação
→ aprendizado
→ candidato
→ proposta
→ autorização explícita
→ integração preparada
→ revisão/merge externo
→ registro em stable
→ rollback registrável
```

## O que a Nyxal pode fazer

- detectar e estruturar uma limitação;
- formular uma hipótese provisória;
- transformar a hipótese em solicitação formal;
- preparar artefato experimental;
- delegar a execução ao laboratório remoto;
- validar SHA, status e métrica;
- comparar com baseline;
- rejeitar regressões;
- persistir experiência e cristal;
- criar candidato e proposta;
- registrar uma autorização explícita fornecida pelo operador;
- preparar uma branch de integração sem tocar stable;
- registrar a integração somente depois de verificar o merge commit em `main`;
- registrar rollback somente depois de verificar o rollback commit em `main`.

## O que continua deliberadamente fora da autonomia

A Nyxal **não** recebe um caminho automático para:

- autorizar a própria proposta;
- fazer merge em `main`;
- executar candidato em stable;
- alterar stable sem autorização externa;
- transformar candidato em integração sem revisão.

A integração é separada em duas fronteiras:

```
autorização
    ↓
preparação de integração
    ↓
revisão/merge externo
    ↓
registro verificável em stable
```

Assim, `proposta`, `candidato` e `stable` permanecem estados distintos.

## Rollback

O rollback mantém o baseline e registra explicitamente o commit que reverteu a integração. O módulo de governança não executa o `git revert`; ele apenas verifica e registra um rollback que já tenha sido produzido no repositório.

## Evidência de implementação

Testes do Nível 9 cobrem:

- evolução controlada determinística;
- laboratório remoto determinístico;
- laboratório remoto E2E;
- ponte Runtime → evolução remota;
- solicitação formal e máquina de estados;
- ciclo formal integrado;
- governança de autorização, integração e rollback.

A validação determinística consolidada foi executada no GitHub Actions após o checkpoint de implementação e passou com sucesso. O workflow também compila os módulos do Nível 9 antes da suite. A validação E2E do laboratório remoto continua sendo uma prova separada, já demonstrada anteriormente. Qualquer falha futura deve ser tratada como regressão/defeito de integração, não como motivo para remover os gates de segurança.
