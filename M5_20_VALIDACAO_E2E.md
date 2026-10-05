# M5.20 — Validação E2E da Cadeia Operacional Governada

## Objetivo

Validar em uma única execução a cadeia integrada construída até M5.19,
sem ampliar a autoridade física do NyxOS.

## Cadeia validada

percepção → fisiologia → plano central → gateway → autorização explícita →
sandbox → rollback → auditoria

## Critérios

- o residente prepara a operação;
- o residente não concede autorização;
- execução sem autorização é bloqueada;
- autorização explícita libera somente a operação permitida;
- a mutação permanece confinada ao sandbox;
- o resultado fornece rollback;
- rollback remove a mutação;
- a auditoria mantém cadeia íntegra;
- o contexto residente não registra integração ou alteração arquitetural.

## Limite

M5.20 é uma validação, não uma expansão de poder.

A execução física continua desabilitada no launcher normal. O teste habilita
explicitamente o sandbox apenas para provar a cadeia controlada em ambiente
temporário.
