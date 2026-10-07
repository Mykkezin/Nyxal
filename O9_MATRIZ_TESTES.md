# O9 — Matriz de Testes

## Entrada

1. `AnaliseOperacional` válida é aceita.
2. Entrada que não é `AnaliseOperacional` é rejeitada.

## Conservação

3. Total de relações é preservado.
4. Total de nós é preservado.
5. Total de ciclos é preservado.
6. Distribuição de autoridades é preservada.
7. Distribuição de tipos é preservada.
8. Distribuição de ciclos é preservada.
9. Distribuição de pares é preservada.

## Rastreabilidade

10. As relações originais continuam identificáveis.
11. Nenhuma relação sintetizada aparece na evidência.
12. A ordem das relações é preservada.

## Epistemologia

13. Autoridade observacional permanece observacional.
14. Autoridade experimental permanece experimental.
15. Autoridade arquitetural nunca é produzida.

## Determinismo

16. A mesma análise produz a mesma identidade.
17. A identidade não depende do instante de execução.

## Imutabilidade

18. Resultado é imutável.
19. Coleções internas são imutáveis.
20. Relações originais não são modificadas.

## Não inferência

21. A→B e B→C não produzem A→C.
22. Frequência não vira regra.
23. Repetição não vira causalidade.
24. Distribuição não vira dependência arquitetural.

## Isolamento

25. Módulo não importa planta.
26. Módulo não importa Runtime.
27. Módulo não acessa filesystem.
28. Módulo não acessa persistência.

## Casos de borda

29. Análise vazia produz evidência vazia válida.
30. Consulta inexistente permanece inexistente.
