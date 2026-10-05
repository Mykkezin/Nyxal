# M5.14 — Plano Central de Controle

## Objetivo

Transformar sinais observados pelo ciclo residente em um plano operacional determinístico e auditável.

Fluxo:

`percepção → fisiologia → plano central → decisão planejada`

## Limite

M5.14 ainda não executa atuação física.

- não controla processos;
- não envia comandos ao host;
- não modifica arquivos de arquitetura;
- não autoriza integração;
- não modifica stable/main;
- não concede conhecimento permanente.

A execução física permanece bloqueada até a camada de gateway de atuação.

## Estados tratados

- normal → aguardar;
- estresse térmico → reduzir carga;
- febre → reduzir carga;
- recuperação → aguardar;
- inicialização/sem sinal → observar;
- falha do ciclo → preservar estado.

O plano recebe evidência já observada; não inventa diagnóstico e não transforma temperatura isolada em autorização de atuação.

## Próxima etapa

M5.15 — presença de máquina / integração progressiva com o gateway de atuação, mantendo a separação entre decisão planejada e execução autorizada.
