# M5.17 — Sandbox Físico Reversível

## Objetivo

Dar ao NyxOS uma primeira capacidade de mutação física real sem liberar
controle sobre o host em geral.

Fluxo:

`plano → gateway → autorização explícita → sandbox físico → resultado → rollback`

## Única mutação física desta etapa

A ação `preservar_estado` cria um arquivo JSON dentro de um diretório sandbox
explicitamente configurado.

O arquivo contém apenas metadados operacionais da própria operação.

A ação `reduzir_carga` continua bloqueada porque ainda não existe executor
físico de processos.

## Contenção

O adaptador:

- resolve o diretório sandbox antes da operação;
- verifica que o alvo permanece dentro do sandbox;
- não usa `subprocess`, `systemctl` ou comandos externos;
- não escreve fora do diretório configurado;
- exige que a capacidade física do sandbox esteja explicitamente habilitada;
- fornece token de rollback;
- permite remover somente artefatos produzidos pelo próprio sandbox.

## Governança

Mesmo com o sandbox habilitado:

- o gateway continua exigindo autorização explícita;
- stable/main não é alterado;
- arquitetura não é modificada pela atuação;
- conhecimento permanente não é promovido automaticamente.

A residência normal continua com execução física desabilitada.

## Validação

O teste verifica:

1. bloqueio quando a capacidade física do sandbox está desligada;
2. bloqueio do gateway sem autorização;
3. criação real do artefato dentro do sandbox após autorização;
4. confirmação de mutação física confinada;
5. rollback real do artefato;
6. bloqueio de `reduzir_carga`.

## Limite atual

M5.17 prova **atuação física reversível e confinada**, não controle geral do
host.

A próxima decisão deve avaliar se vale avançar para um segundo tipo de ação
reversível ou consolidar métricas, auditoria e rollback antes de ampliar o
alcance físico.
