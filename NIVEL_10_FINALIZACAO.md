# Nível 10 — Checkpoint de Implementação

## Estado

**Implementação:** concluída nesta etapa.  
**Certificação final:** pendente de execução/status do CI.

## Componentes presentes

- `NIVEL_10_CONTRATO.md`
- `nixal_observador_desenvolvimento.py`
- `nixal_ciclo_local_nivel10.py`
- `nixal_executor_ciclo_local_nivel10.py`
- `teste_nivel_10_contrato.py`
- `teste_nivel_10_observador_desenvolvimento.py`
- `teste_nivel_10_ciclo_local.py`
- `teste_nivel_10_executor.py`
- `teste_nivel_10_suite_final.py`

## Fluxo implementado

```
observado
  ↓
alteracao_detectada
  ↓
sincronizacao_preparada
  ↓
validacao_em_execucao
  ↓
validacao_concluida
  ├──→ aprovado
  └──→ rejeitado
```

## Evidências cobertas pela suíte

- contrato formal presente;
- detecção determinística de commit;
- ausência de falso positivo;
- persistência do histórico;
- identidade determinística do ciclo;
- preservação do observador legado;
- bloqueio de estado persistente adulterado;
- transições válidas;
- transições inválidas bloqueadas;
- aprovação sem autorização;
- rejeição por falha de validação;
- encerramento auditável de exceção técnica;
- nova tentativa explícita de ciclo rejeitado;
- bloqueio por branch incorreta;
- bloqueio por árvore de trabalho suja.

## Invariantes

- `main` não é modificada pelo ciclo;
- o ciclo não faz merge;
- o ciclo não concede autorização;
- aprovação de validação não autoriza integração;
- candidatos externos não são executados pelo ciclo;
- dependências não são instaladas automaticamente;
- registros anteriores não são apagados.

## Relação com Nível 9

Uma execução Nível 10 em estado `aprovado` somente produz evidência de validação.
Qualquer integração em `stable` continua subordinada aos gates externos do Nível 9.

## Gate restante

É necessária uma execução final do workflow de validação pelo GitHub Actions e
registro do resultado como evidência de CI.

Até essa evidência existir, o Nível 10 deve ser classificado como:

**IMPLEMENTADO / AGUARDANDO CERTIFICAÇÃO CI**

e não como formalmente concluído.

## Próxima transição

Somente após CI verde:

```
Nível 10 implementado
        ↓
regressão Nível 9 + Nível 10
        ↓
checkpoint certificado
        ↓
Nível 10 concluído
        ↓
definição formal do Nível 11
```
