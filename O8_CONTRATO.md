# O8 — Análise Operacional do Grafo

## Objetivo

O8 recebe exclusivamente um `GrafoOperacional` já construído e validado
pelo O7 e produz uma análise determinística das propriedades diretamente
demonstráveis pela topologia contida nesse grafo.

O8 não cria evidência nova e não transforma análise em arquitetura,
causalidade, aprendizado ou autorização.

## Entrada

A entrada obrigatória é:

`GrafoOperacional`

Entradas brutas, relações não normalizadas ou estruturas externas são
rejeitadas.

## Saída

A saída é:

`AnaliseOperacional`

A estrutura é imutável.

## Propriedades permitidas

A análise pode calcular somente propriedades diretamente observáveis ou
matematicamente deriváveis das relações presentes:

- nós presentes;
- quantidade de nós;
- quantidade de relações;
- quantidade de ciclos;
- relações por ciclo;
- autoridades presentes;
- contagem por autoridade;
- contagem por tipo;
- ocorrência de pares origem/destino;
- relações que correspondem exatamente a origem/destino;
- relações que pertencem exatamente a um ciclo.

## Proibições

O8 não pode:

- inferir causalidade;
- inferir dependência arquitetural;
- produzir autoridade arquitetural;
- alterar relações;
- remover relações;
- deduplicar relações;
- criar relações;
- criar caminhos transitivos;
- alterar o GrafoOperacional;
- acessar a planta;
- acessar o Runtime;
- acessar Delta;
- acessar memória permanente;
- executar autorização;
- executar integração;
- escrever no filesystem;
- alterar stable;
- alterar main.

## Invariantes

### O8-I1 — Conservação

Todas as relações consultadas continuam exatamente as mesmas.

### O8-I2 — Sem inferência

Somente propriedades matemáticas diretamente deriváveis da entrada podem
ser retornadas.

### O8-I3 — Conservação epistemológica

A análise preserva a distinção entre:

- `observacional`
- `experimental`

### O8-I4 — Sem autoridade arquitetural

Nenhum resultado de análise pode possuir autoridade arquitetural.

### O8-I5 — Sem causalidade implícita

A existência de A→B e B→C não autoriza concluir A→C.

### O8-I6 — Isolamento

O8 não possui dependência da planta, Runtime, Delta, persistência ou
mecanismos de integração.

### O8-I7 — Imutabilidade

O resultado da análise é imutável.

### O8-I8 — Rastreabilidade

Resultados derivados de relações devem manter referência direta às relações
que os sustentam.

## Limite epistemológico

O8 responde:

> "O que este grafo demonstra topologicamente?"

O8 não responde:

> "O que a arquitetura deve ser?"

nem:

> "O que causou o quê?"

nem:

> "O que Nyxal deve aprender?"

## Estado

O8 permanece isolado e experimental até validação e revisão posteriores.
