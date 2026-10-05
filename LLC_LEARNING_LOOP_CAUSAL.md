# LLC — Learning Loop Causal

## Estado atual: LLC.5 implementado e validado

O LLC possui cinco etapas:

1. **LLC.1 — influencia decisória**
2. **LLC.2 — feedback operacional**
3. **LLC.3 — protocolo de evidência causal controlada**
4. **LLC.4 — evidência ambiental real/observacional**
5. **LLC.5 — evidência causal longitudinal do habitat**

## LLC.4

A quarta etapa aproxima o Learning Loop do habitat real sem pular a etapa experimental.

O componente `EvidenciaAmbientalLLC` usa o `HabitatNixOS` existente em modo somente leitura e pode:

- capturar um snapshot real do host;
- identificar o snapshot por hash determinístico;
- observar métricas numéricas declaradas;
- comparar antes/depois;
- registrar fonte, unidade, direção de melhoria e ids dos snapshots.

Uma mudança real observada no host continua sendo evidência observacional.

## LLC.5

A quinta etapa testa uma propriedade arquitetural concreta:

> uma mudança ambiental observada pode ser vinculada a uma transição LLC explicitamente identificada e repetida longitudinalmente dentro de um desenho controlado, sem atribuir causalidade por simples correlação.

Cada repetição declara explicitamente:

- `transicao_id`;
- `ciclo_id`;
- ação esperada e decisão LLC;
- influência decisória comprovada;
- resultado da ação;
- snapshot ambiental antes/depois da intervenção;
- snapshot ambiental antes/depois do controle;
- métrica, unidade, fonte e direção.

O protocolo exige pelo menos **3 transições e 3 ciclos distintos**, a mesma ação esperada e a mesma métrica declarada em todas as repetições.

Para cada repetição:

```
efeito =
(intervenção_depois - intervenção_antes)
-
(controle_depois - controle_antes)
```

O gate longitudinal passa somente quando todas as transições são válidas, os pares estão em ordem temporal, a decisão possui influência decisória comprovada e o efeito melhora na mesma direção em todas as repetições.

O resultado é classificado como:

```
evidencia_causal_longitudinal = true
causalidade_ambiental_comprovada = true
```

quando todos os gates passam.

Essa afirmação é limitada ao desenho e aos dados fornecidos. Não representa causalidade universal fora do protocolo.

## Integração

LLC.4 e LLC.5 não alteram o Runtime para coletar automaticamente métricas ambientais em todos os ciclos.

A captura e a avaliação longitudinal precisam ser invocadas explicitamente por uma camada que conheça o desenho de medição.

Não existe:

- treinamento automático;
- deployment automático;
- autoalteração;
- memória paralela;
- boot adicional;
- autorização implícita;
- integração automática em `main`.

## Validação

O LLC.5 possui teste dedicado para:

- evidência longitudinal aprovada;
- repetição mínima;
- influência decisória ausente;
- ação divergente;
- compatibilidade com o formato de observação do LLC.4;
- invariantes de governança;
- ausência de execução externa.

M5 permanece congelado.

A branch `feat/llc-learning-loop` continua separada de `main`.
