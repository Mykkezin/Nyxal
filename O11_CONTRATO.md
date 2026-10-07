# O11 — Reutilização Controlada de Evidência

## 1. Objetivo

Permitir a reutilização determinística de evidência operacional já
qualificada pelo O10, sem alterar a evidência original e sem produzir
novo conhecimento.

O11 é uma operação de seleção controlada sobre evidência existente.

---

## 2. Entradas

O11 recebe:

1. uma `EvidenciaOperacional`;
2. uma `QualificacaoEvidencia`;
3. um critério explícito de seleção.

A qualificação deve estar no estado:

`qualificada`

A identidade declarada pela qualificação deve ser exatamente igual
à identidade da evidência.

A evidência deve disponibilizar as relações operacionais originais
consolidadas pelo O9.

---

## 3. Critérios permitidos

Os critérios iniciais são exatos:

- `identidade`
- `par`
- `ciclo`
- `autoridade`
- `tipo`

Não existe inferência entre critérios.

Não existe consulta semântica.

Não existe busca aproximada.

---

## 4. Saída

O11 produz `ReutilizacaoEvidencia`.

A saída é imutável e contém:

- identidade da evidência;
- identidade da qualificação;
- critério utilizado;
- relações selecionadas;
- quantidade selecionada.

As relações retornadas são referências exatas às relações originais.

---

## 5. Regras epistemológicas

O11 NÃO:

- cria relações;
- altera relações;
- deduplica relações;
- ordena semanticamente relações;
- infere causalidade;
- infere transitividade;
- cria dependências arquiteturais;
- produz autoridade arquitetural;
- produz aprendizado;
- modifica memória permanente;
- modifica Runtime;
- modifica planta;
- modifica Delta;
- autoriza integração;
- executa integração;
- acessa filesystem;
- acessa rede;
- altera `main`.

---

## 6. Regra de qualificação

Uma evidência rejeitada pelo O10 não pode ser reutilizada pelo O11.

Se:

`qualificacao.estado != "qualificada"`

a operação deve falhar.

---

## 7. Regra de identidade

A reutilização somente é válida quando:

`qualificacao.identidade == evidencia.identidade`

Qualquer divergência rejeita a operação.

---

## 8. Conservação

O11 somente pode devolver relações já existentes na evidência.

Nenhuma relação nova pode aparecer na saída.

A ordem original das relações deve ser preservada.

Duplicatas legítimas devem permanecer preservadas.

---

## 9. Isolamento

O11 é uma camada operacional pura.

Não possui acesso a:

- Runtime;
- planta;
- memória;
- aprendizado;
- Delta;
- autorização;
- integração;
- filesystem;
- rede;
- Git.

---

## 10. Determinismo

A mesma evidência, qualificação e critério devem produzir
a mesma reutilização.

A reutilização não depende do instante da execução.

---

## 11. Limite explícito

Reutilizar uma evidência não significa:

- acreditar nela como verdade causal;
- transformá-la em conhecimento;
- transformá-la em aprendizado;
- promovê-la à arquitetura.

O11 apenas permite consultar novamente aquilo que O10 já declarou
estruturalmente qualificado.

---

## 12. Fronteira O11 → O12

O11 termina na reutilização controlada.

Qualquer comparação entre evidências pertence ao O12.

Qualquer identificação de recorrência pertence ao O13.

Qualquer candidato a aprendizado pertence ao O14.

Qualquer fechamento da cadeia pertence ao O15.
