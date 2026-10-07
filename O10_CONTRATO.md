# O10 — Qualificação da Evidência Operacional

## Objetivo

O10 recebe exclusivamente uma `EvidenciaOperacional` produzida pelo O9 e
verifica se ela satisfaz requisitos estruturais de integridade,
consistência e rastreabilidade.

O10 qualifica a forma da evidência.

O10 não qualifica causalidade, verdade arquitetural ou aprendizado.

## Entrada

A entrada obrigatória é:

`EvidenciaOperacional`

Qualquer outra estrutura é rejeitada.

## Saída

A saída é:

`QualificacaoEvidencia`

A estrutura é imutável.

## Critérios de qualificação

Uma evidência pode ser qualificada quando:

1. possui identidade;
2. possui cardinalidades coerentes;
3. possui relações rastreáveis;
4. a quantidade de relações coincide com `total_relacoes`;
5. os nós declarados pelas relações são compatíveis com `total_nos`;
6. os ciclos presentes são compatíveis com `total_ciclos`;
7. as distribuições de autoridade são coerentes;
8. as distribuições de tipos são coerentes;
9. as distribuições de ciclos são coerentes;
10. as distribuições de pares são coerentes;
11. nenhuma relação sintetizada é detectada;
12. a identidade corresponde ao conteúdo consolidado.

## Estados

A qualificação possui somente dois estados:

- `qualificada`
- `rejeitada`

`qualificada` significa:

> A estrutura da evidência é internamente consistente e rastreável.

Não significa:

- causalidade comprovada;
- verdade arquitetural;
- aprendizado válido;
- regra permanente;
- autorização;
- integração.

## Proibições

O10 não pode:

- alterar a evidência;
- criar evidência;
- criar relações;
- deduplicar relações;
- inferir causalidade;
- inferir dependência arquitetural;
- produzir autoridade arquitetural;
- produzir aprendizado;
- modificar memória;
- modificar Runtime;
- modificar planta;
- modificar Delta;
- executar autorização;
- executar integração;
- acessar filesystem;
- alterar stable;
- alterar main.

## Invariantes

### O10-I1 — Conservação

A evidência original permanece exatamente inalterada.

### O10-I2 — Integridade cardinal

As cardinalidades declaradas devem corresponder às relações efetivamente
presentes.

### O10-I3 — Integridade topológica

Nós, ciclos e pares devem ser compatíveis com as relações.

### O10-I4 — Integridade epistemológica

As autoridades presentes devem continuar exatamente as mesmas.

### O10-I5 — Integridade de identidade

A identidade deve corresponder ao conteúdo da evidência.

### O10-I6 — Rastreabilidade

Toda qualificação deve poder ser explicada pelas estruturas presentes na
evidência.

### O10-I7 — Sem inferência

Qualificação estrutural não cria qualquer conclusão nova sobre causalidade
ou arquitetura.

### O10-I8 — Isolamento

O10 permanece independente da planta, Runtime, persistência e mecanismos de
evolução.

## Limite epistemológico

O10 responde:

> "Esta evidência está estruturalmente íntegra e rastreável?"

O10 não responde:

> "Esta evidência prova causalidade?"

nem:

> "Esta evidência deve virar aprendizado?"

nem:

> "A arquitetura deve mudar?"

## Estado

O10 permanece isolado e experimental.
