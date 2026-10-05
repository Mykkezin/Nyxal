# M5.15 — Gateway Governado de Atuação

## Objetivo

Criar a fronteira explícita entre uma decisão planejada pelo NyxOS e qualquer futura atuação sobre o host.

Fluxo:

`percepção → fisiologia → plano central → gateway → atuação autorizada`

## O que existe

`GatewayAtuacaoNixOS`:

- recebe um plano já produzido pelo M5.14;
- valida a ação contra uma allowlist;
- cria uma operação auditável com `plano_id` e `operacao_id`;
- separa preparação de execução;
- exige autorização explícita para qualquer execução;
- permite um executor injetado somente para integração controlada;
- mantém persistência opcional do último estado.

## Limite padrão

A execução física permanece **desabilitada por padrão**.

Sem autorização explícita:
- a operação é bloqueada;
- o executor não é chamado.

Mesmo com autorização explícita, a operação continua bloqueada enquanto `execucao_fisica_habilitada=False`.

O M5.15 não concede autorização automaticamente, não controla processos por conta própria, não altera arquitetura e não modifica `main`/stable.

## Validação

O teste cobre:

1. plano de febre produzindo `reduzir_carga`;
2. preparação da operação;
3. bloqueio sem autorização;
4. bloqueio pela desabilitação física padrão;
5. execução somente no cenário explicitamente habilitado e autorizado;
6. confirmação de que o executor não é chamado nos cenários bloqueados.

## Próxima etapa

Integrar o gateway ao ciclo residente em modo **somente preparação/bloqueio**, mantendo a execução física desligada. A ativação física deve continuar sendo uma decisão governada e separada.
