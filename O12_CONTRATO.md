# O12 — Comparação de Evidências

## 1. Objetivo

Comparar duas ou mais evidências operacionais que já tenham sido
qualificadas pelo O10.

O12 identifica diferenças e interseções estruturais entre evidências.

A comparação não modifica nenhuma evidência de entrada.

---

## 2. Entradas

Cada entrada deve conter:

- identidade;
- estado de qualificação;
- relações operacionais;
- estrutura imutável.

Somente evidências com estado:

`qualificada`

podem participar da comparação.

---

## 3. Unidade da comparação

A comparação ocorre sobre relações operacionais.

São considerados:

- relações em comum;
- relações exclusivas da primeira evidência;
- relações exclusivas da segunda evidência;
- cardinalidade;
- identidade das evidências.

A comparação é estrutural.

Não existe interpretação semântica.

---

## 4. Definições

Para duas evidências A e B:

### Interseção

Relações presentes em A e B.

### Exclusivas A

Relações presentes em A e ausentes em B.

### Exclusivas B

Relações presentes em B e ausentes em A.

### Igualdade

A e B possuem exatamente a mesma sequência de relações.

### Sobreposição

A e B possuem pelo menos uma relação em comum.

---

## 5. Preservação

As relações originais devem ser preservadas.

O12 não:

- altera relações;
- normaliza relações;
- deduplica relações;
- cria relações;
- cria relações transitivas;
- cria causalidade;
- modifica timestamps;
- modifica ciclos;
- modifica proveniência;
- modifica autoridade.

---

## 6. Autoridade

A comparação não aumenta autoridade.

Nenhum resultado de comparação pode ser classificado como:

`autoridade=arquitetural`

ou equivalente.

A comparação apenas descreve o conteúdo estrutural recebido.

---

## 7. Aprendizado

O12 não produz aprendizado.

O12 não produz:

- regra aprendida;
- memória permanente;
- cristalização;
- hipótese;
- integração;
- alteração arquitetural.

Uma diferença entre evidências não é, por si só, um padrão.

Uma interseção entre evidências não é, por si só, uma causalidade.

---

## 8. Determinismo

A mesma dupla de evidências deve produzir o mesmo resultado.

A ordem das entradas é significativa apenas para identificar:

- exclusivas da primeira;
- exclusivas da segunda.

A interseção é simétrica.

---

## 9. Imutabilidade

O resultado da comparação é imutável.

As evidências de entrada permanecem imutáveis.

As relações retornadas são as próprias relações originais.

---

## 10. Escopo

O12 é uma camada operacional pura.

Não acessa:

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

## 11. Fronteiras

O10:

qualifica.

O11:

reutiliza.

O12:

compara.

O13:

detecta recorrência.

O14:

produz candidato a aprendizado.

O15:

fecha a cadeia operacional.

LLC:

realiza o mecanismo formal de aprendizado auditável.

---

## 12. Regra fundamental

Comparar evidências não significa explicar por que elas diferem.

O12 descreve diferenças observáveis.

Explicações causais dependem de evidências adicionais e não são
criadas pela comparação.
