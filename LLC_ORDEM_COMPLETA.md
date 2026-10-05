# LLC — Ordem Completa

## Cadeia consolidada

1. LLC.1 — Influência decisória
   - prova que aprendizado válido pode alterar uma escolha.

2. LLC.2 — Feedback operacional
   - conecta decisão, ação, resultado observado e feedback.

3. LLC.3 — Evidência causal controlada
   - exige contraste controlado, contrafactual e repetição.

4. LLC.4 — Evidência ambiental observacional
   - conecta a avaliação ao habitat real em modo somente leitura.

5. LLC.5 — Evidência causal longitudinal
   - exige múltiplos ciclos, mesma ação/métrica, controle, temporalidade, influência decisória e consistência direcional.

6. LLC.6 — Integridade de proveniência
   - verifica a origem determinística da evidência do LLC.4 antes de seu uso causal.

7. LLC.7 — Replicação distinta verificável
   - exige IDs distintos de replicação, execução e série, mesma ação e métrica, proveniência válida e direção consistente.
   - não declara independência real sem uma fonte experimental que a demonstre.

8. LLC.8 — Limite de escopo
   - impede extrapolar o resultado observado para uma afirmação universal.

9. LLC.9 — Aprendizado auditável
   - transforma evidência com escopo validado em uma regra identificável, preservando a proveniência.

10. LLC.10 — Fechamento do loop
    - verifica que o aprendizado auditável influencia uma reutilização posterior da decisão.

## Fluxo

percepção
→ decisão
→ ação
→ resultado
→ feedback
→ controle
→ evidência ambiental
→ longitudinal
→ proveniência
→ replicação distinta
→ escopo
→ aprendizado auditável
→ reutilização
→ validação

## Limite da cadeia

LLC.7 usa separação declarada de execuções e séries como gate de replicação distinta. Isso não é prova de independência experimental real.

Uma futura camada de laboratório poderá provar independência experimental quando houver dados de execução adequados. Não será inventada uma prova de independência a partir de IDs.

## Governança

Nenhuma LLC autoriza, por si só:
- alteração de stable;
- integração em main;
- treinamento automático;
- autoalteração arquitetural;
- implantação automática;
- causalidade universal.

## Validação integrada

O teste teste_llc_completo.py valida LLC.7–LLC.10 e seus gates positivos e negativos.

Antes do checkpoint final, o CI deve executar:
- validação existente de LLC;
- LLC.4;
- LLC.5;
- LLC.6;
- teste integrado LLC.7–LLC.10.

Só depois disso a cadeia completa deve ser considerada validada.
