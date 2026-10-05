# M5.18 — Auditoria Encadeada de Atuação

## Objetivo

Registrar a cadeia de atuação física de forma verificável, antes de ampliar o
alcance físico do NyxOS.

Fluxo:

preparação → bloqueio/autorização → execução → mutação confinada → rollback

## Auditoria

AuditoriaAtuacaoNixOS grava eventos em JSONL e encadeia cada registro por
hash_anterior + hash.

A validação recompõe o hash de cada registro e verifica:

- sequência contínua;
- vínculo com o registro anterior;
- integridade do conteúdo;
- último hash da cadeia.

Isso fornece rastreabilidade de execução. Não deve ser interpretado como
imutabilidade criptográfica do arquivo no sistema operacional.

## Eventos atuais

- operacao_preparada
- operacao_bloqueada
- atuacao_sandbox_executada
- operacao_executada
- rollback_executado

## Limites

M5.18 não amplia as ações físicas disponíveis.

- preservar_estado continua confinado ao sandbox;
- reduzir_carga continua bloqueado;
- autorização explícita continua obrigatória;
- stable/main não é alterada pela atuação;
- não há promoção automática de conhecimento.

## Próximo passo

Usar a auditoria para avaliar a estabilidade da cadeia física antes de
considerar qualquer nova ação mutável.
