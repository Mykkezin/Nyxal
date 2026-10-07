# LLC — Learning Loop Causal

## Estado atual: LLC.1 → LLC.10 implementado e validado

A linha LLC foi expandida e validada até o fechamento do loop:

1. **LLC.1 — influência decisória**
2. **LLC.2 — feedback operacional**
3. **LLC.3 — evidência causal controlada**
4. **LLC.4 — evidência ambiental observacional**
5. **LLC.5 — evidência causal longitudinal**
6. **LLC.6 — integridade de proveniência**
7. **LLC.7 — replicação distinta verificável**
8. **LLC.8 — limite de escopo**
9. **LLC.9 — aprendizado auditável**
10. **LLC.10 — fechamento do loop**

A cadeia completa está descrita em `LLC_ORDEM_COMPLETA.md` e possui teste integrado em `teste_llc_completo.py`.

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

A quinta etapa vincula uma mudança ambiental observada a uma transição LLC explicitamente identificada e repetida longitudinalmente dentro de um desenho controlado.

Cada repetição declara:

- `transicao_id`;
- `ciclo_id`;
- ação esperada e decisão LLC;
- influência decisória comprovada;
- resultado da ação;
- snapshots ambientais;
- métrica, unidade, fonte e direção.

O protocolo exige múltiplas transições/ciclos, a mesma ação esperada e a mesma métrica declarada nas repetições. O efeito contrafactual é calculado pela diferença entre a variação da intervenção e a variação do controle.

A afirmação causal permanece limitada ao desenho e aos dados fornecidos.

## LLC.6 → LLC.10

A proveniência valida a origem determinística da evidência antes do uso causal.

A replicação verifica separação declarada de execuções e séries.

O escopo impede extrapolação universal.

O aprendizado transforma evidência com escopo validado em uma regra identificável, preservando sua proveniência.

O fechamento verifica que o aprendizado auditável influencia uma reutilização posterior da decisão.

## Integração

A cadeia LLC não altera o Runtime para coletar automaticamente métricas ambientais em todos os ciclos.

Não existe:

- treinamento automático;
- deployment automático;
- autoalteração;
- memória paralela;
- autorização implícita;
- integração automática em `main`.

## Validação

A validação integrada existente cobre LLC.7–LLC.10 e seus gates positivos e negativos.

O CI do projeto executa as validações de LLC, incluindo LLC.4, LLC.5, LLC.6 e a suíte integrada.

O estado considerado atual é **implementado e validado**, sem concessão de autoridade de integração ou autoalteração.

## Governança

Nenhuma etapa LLC autoriza, por si só:

- alteração de stable;
- integração em main;
- treinamento automático;
- autoalteração arquitetural;
- implantação automática;
- causalidade universal.

M5 permanece encerrado no estado registrado pelos checkpoints pós-M5.23 e pós-M5.24.
