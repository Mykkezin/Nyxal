# M5.12 — Corpo Térmico e Ventilação

## Objetivo

Transformar os sensores térmicos já observados pelo corpo computacional em um estado térmico consolidado, detectar tendência e preparar um plano de resfriamento com histerese e fallback.

## Estado térmico

M5.12 reutiliza os limiares já presentes no corpo computacional:

- abaixo de 40 °C: `fria`;
- 40 °C a menos de 65 °C: `normal`;
- 65 °C a menos de 80 °C: `quente`;
- 80 °C ou mais: `muito_quente`.

Uma histerese de 3 °C evita alternância imediata ao redor dos limites.

## Tendência

O módulo compara duas amostras e classifica o comportamento como:

- `subindo`;
- `descendo`;
- `estavel`.

## Ventilação

O NyxOS descobre interfaces PWM expostas por `hwmon`, mas não escreve nesses controles neste marco.

O planejador produz uma intenção supervisionada:

```
normal/fria → manter_resfriamento
quente     → aumentar_resfriamento_supervisionado
muito_quente → maximizar_resfriamento_supervisionado
```

Sem sensor térmico confiável, o fallback é **não atuar**.

## Governança

M5.12 não habilita:

- controle automático contínuo de ventoinhas;
- escrita automática em `/sys/class/hwmon`;
- alteração de limites pelo Qwen;
- autoridade de evolução;
- integração em `main`.

O próximo marco ainda deverá definir uma fronteira física supervisionada antes de permitir qualquer controle automático contínuo.

## Validação

O teste M5.12 cobre limiares, histerese, tendência, agregação da temperatura máxima, planejamento de ventilação e fallback sem sensor.