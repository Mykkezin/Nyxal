# M5.19 — Integração Residente da Atuação Governada

## Objetivo

Fechar a integração arquitetural entre o ciclo residente, o gateway, o sandbox
físico e a auditoria, sem habilitar mutação física no modo normal.

Fluxo residente:

percepção → fisiologia → plano → gateway → sandbox disponível → auditoria

A execução física permanece desligada.

## Estado

O launcher residente passa a construir:

- AuditoriaAtuacaoNixOS;
- AdaptadorSandboxFisicoNixOS;
- GatewayAtuacaoNixOS com sandbox como executor.

Configuração normal:

- sandbox físico: desabilitado;
- gateway físico: desabilitado;
- autorização: nunca concedida automaticamente;
- auditoria: ativa.

## Validação

O teste executa um ciclo residente e confirma:

1. plano preparado;
2. operação de gateway preparada;
3. executor sandbox disponível;
4. nenhuma mutação física;
5. registro de auditoria;
6. cadeia de auditoria íntegra.

## Limite

M5.19 não concede autonomia física ao residente. Ele fecha a integração das
camadas e mantém a fronteira física explicitamente desabilitada.
