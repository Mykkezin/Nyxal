# LLC — Learning Loop Causal

## Estado atual: LLC.4 iniciado

O LLC possui quatro etapas:

1. **LLC.1 — influencia decisoria**
2. **LLC.2 — feedback operacional**
3. **LLC.3 — protocolo de evidencia causal controlada**
4. **LLC.4 — evidencia ambiental real/observacional**

## LLC.4

A quarta etapa aproxima o Learning Loop do habitat real sem pular a etapa experimental.

O novo componente `EvidenciaAmbientalLLC` usa o `HabitatNixOS` existente em modo somente leitura e pode:

- capturar um snapshot real do host;
- identificar o snapshot por hash deterministico;
- observar metricas numericas declaradas;
- comparar antes/depois;
- registrar fonte, unidade, direcao de melhoria e ids dos snapshots.

Metricas atualmente declaradas incluem CPU, memoria, armazenamento, processos, uptime e leituras numericas de GPU quando disponiveis.

## Regra central

LLC.4 produz:

```
evidencia_ambiental_observacional = true
```

Mas mantém:

```
causalidade_ambiental_comprovada = false
```

Uma mudanca real observada no host nao e automaticamente atribuida a acao do LLC.

O resultado:

```
acao -> mudanca observada
```

continua sendo observacional.

Para atribuir efeito causal ainda e necessario passar pelo protocolo controlado do LLC.3 com desenho experimental, controle, contrafactual e repeticoes adequadas.

## Integracao

LLC.4 nao altera o Runtime residente para coletar metricas automaticamente em todos os ciclos.

A captura pode ser chamada explicitamente por uma camada superior que conheca o desenho da medicao.

Nao existe:

- treinamento automatico;
- deployment;
- autoalteracao;
- nova memoria;
- boot adicional;
- autorizacao implicita;
- integracao em `main`.

## Validacao

O teste dedicado verifica:

- captura sintetica estruturada;
- captura real do HabitatNixOS em somente leitura;
- observacao de metrica declarada;
- comparacao antes/depois;
- rejeicao de metrica nao declarada;
- invariantes de governanca.

## Estado

`LLC.4.0.0` — interface de evidencia ambiental real/observacional implementada e validada.

M5 permanece congelado.

A branch `feat/llc-learning-loop` continua separada de `main`.
