# O13 — Detecção de Padrões Recorrentes

## 1. Objetivo

Identificar padrões estruturais que aparecem repetidamente em um
conjunto de evidências operacionais já qualificadas.

O13 transforma repetição observável em uma descrição estruturada
de recorrência.

O13 não transforma recorrência em aprendizado.

---

## 2. Entrada

O13 recebe um conjunto ordenado de evidências operacionais.

Cada evidência deve:

- possuir identidade;
- estar qualificada;
- possuir relações operacionais;
- preservar sua estrutura original.

Evidências não qualificadas são rejeitadas.

---

## 3. Unidade do padrão

Um padrão recorrente é definido por uma assinatura estrutural
observável.

A assinatura inicial utiliza:

- origem;
- destino;
- tipo;
- autoridade.

O ciclo não integra a assinatura estrutural principal porque o mesmo
padrão pode aparecer em ciclos diferentes.

O ciclo permanece disponível como ocorrência.

---

## 4. Ocorrência

Cada ocorrência registra:

- identidade da evidência;
- ciclo observado;
- posição da relação dentro da evidência.

A ocorrência é uma referência à relação original.

Nenhuma relação nova é criada.

---

## 5. Recorrência

Um padrão é considerado recorrente quando aparece em pelo menos
duas evidências distintas.

A identidade da evidência é usada para garantir que duas ocorrências
da mesma evidência não sejam tratadas como replicações independentes.

---

## 6. Independência

O13 não declara independência causal ou experimental.

Duas evidências diferentes são apenas evidências diferentes.

A condição:

`evidência A != evidência B`

não implica:

`A e B são independentes`.

Qualquer avaliação formal de independência permanece fora do O13.

---

## 7. Resultado

O13 produz:

`PadraoRecorrente`

contendo:

- assinatura;
- ocorrências;
- identidades das evidências;
- ciclos observados;
- frequência de evidências distintas.

O resultado é imutável.

---

## 8. Determinismo

A mesma coleção de evidências deve produzir os mesmos padrões.

A ordenação dos padrões deve ser determinística.

A ordenação das ocorrências deve preservar a ordem das evidências
de entrada e das relações dentro de cada evidência.

---

## 9. Preservação

O13 não:

- modifica evidências;
- modifica relações;
- cria relações;
- deduplica relações;
- cria causalidade;
- cria transitividade;
- aumenta autoridade;
- altera ciclos;
- altera proveniência;
- altera timestamps.

---

## 10. Aprendizado

O13 não produz:

- aprendizado;
- regra aprendida;
- memória permanente;
- cristalização;
- hipótese;
- integração;
- alteração arquitetural.

Uma recorrência é apenas uma propriedade observada do conjunto
de evidências recebido.

---

## 11. Limite epistemológico

O13 pode afirmar:

"o mesmo padrão estrutural foi observado em N evidências distintas."

O13 não pode afirmar:

"o padrão é verdadeiro."

O13 não pode afirmar:

"o padrão é causal."

O13 não pode afirmar:

"o padrão deve ser reutilizado."

O13 não pode afirmar:

"o sistema aprendeu."

---

## 12. Isolamento

O13 não acessa:

- Runtime;
- planta;
- Delta;
- memória;
- aprendizado;
- filesystem;
- rede;
- Git;
- autorização;
- integração.

---

## 13. Fronteira

O10:

qualifica evidências.

O11:

reutiliza evidências.

O12:

compara evidências.

O13:

detecta recorrência.

O14:

produz candidato a aprendizado.

O15:

fecha a cadeia operacional.

LLC:

realiza o aprendizado auditável.

---

## 14. Regra fundamental

Recorrência não é aprendizado.

O13 somente torna a recorrência explicitamente observável,
determinística e auditável.
