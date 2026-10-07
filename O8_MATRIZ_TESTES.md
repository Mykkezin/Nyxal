# O8 — Matriz de Testes

## Entrada

1. GrafoOperacional válido é aceito.
2. Entrada que não é GrafoOperacional é rejeitada.

## Conservação

3. Quantidade de relações preservada.
4. Quantidade de nós calculada sem alterar o grafo.
5. Relações duplicadas continuam sendo contadas individualmente.
6. Relações com mesma origem/destino continuam distintas quando possuem
   evidências, instantes ou ciclos diferentes.

## Ciclos

7. Ciclos distintos permanecem distintos.
8. Ciclo `None` permanece distinto de string `"None"`.
9. Relações sem ciclo permanecem no bucket correspondente.

## Autoridade

10. Autoridade observacional permanece observacional.
11. Autoridade experimental permanece experimental.
12. Resultado nunca cria autoridade arquitetural.

## Tipos

13. Tipos existentes são apenas contabilizados.
14. Nenhum novo tipo é inventado.

## Topologia

15. A→B e B→C não gera A→C.
16. Consulta A→B retorna somente relações A→B.
17. Nós são derivados somente de origem/destino presentes.
18. Nenhuma resolução contra a planta é realizada.

## Imutabilidade

19. Resultado não pode ser alterado.
20. Coleções retornadas são imutáveis.
21. Grafo original permanece inalterado.

## Isolamento

22. O módulo não importa planta.
23. O módulo não importa Runtime.
24. O módulo não acessa filesystem.
25. O módulo não acessa persistência.

## Casos de borda

26. Grafo vazio produz análise vazia válida.
27. Ciclos inexistentes produzem contagem zero.
28. Consulta sem correspondência retorna coleção vazia.

## Rastreabilidade

29. Resultados de consulta retornam as próprias instâncias das relações
   originais.
30. Nenhuma relação sintetizada é criada.
