# LLC — Learning Loop Causal

## Objetivo

O LLC e a proxima camada do Nyxal depois do fechamento do M5. Seu primeiro objetivo e provar uma propriedade especifica:

aprendizado anterior -> influencia observavel na decisao -> escolha A ou B.

O LLC nao tenta resolver toda a aprendizagem de uma vez. A primeira entrega e uma politica decisoria pequena, deterministica e auditavel.

## O que esta sendo provado

O Runtime ja registrava aprendizado e o entregava ao ciclo seguinte, mas isso nao provava que o aprendizado mudava a escolha.

O LLC cria uma comparacao explicita:

decisao_sem_aprendizado
versus
decisao_com_aprendizado

Se o mesmo estado e a mesma prioridade produzem escolhas diferentes apenas porque um sinal de aprendizado estruturado foi aplicado, a influencia decisoria fica comprovada para aquele ciclo.

## Politica inicial

A politica experimental da primeira versao e:

repetir_sucesso_evitar_falha

Existem duas alternativas previamente registradas:

1. registrar_estado_corpo
2. observar_sem_atuar

Sem aprendizado, a escolha deterministica e registrar_estado_corpo.

Se a experiencia anterior mostra sucesso da mesma acao, a politica aumenta sua pontuacao e a escolha permanece.

Se a experiencia anterior mostra falha da mesma acao, a politica reduz sua pontuacao e favorece observar_sem_atuar.

Esta politica e somente um mecanismo de prova do LLC. Ela nao e a politica definitiva de comportamento do Nyxal.

## Causalidade

O LLC faz uma afirmacao limitada:

influencia_decisoria_comprovada = true

somente quando:
- existe aprendizado estruturado valido;
- esse aprendizado foi marcado como aplicado ao ciclo;
- a decisao com aprendizado difere da decisao contrafactual sem aprendizado.

Isso prova dependencia decisoria dentro da politica deterministica.

Nao prova ainda que a decisao melhorou o ambiente. Por isso:

causalidade_ambiental_comprovada = false

permanece invariavel nesta etapa.

## Integracao com Runtime

O Runtime recebe o LLC por injecao opcional e somente usa a camada quando ela e fornecida explicitamente.

No modo padrao, sem LLC:
Runtime -> _decidir -> decisao historica da Fase 01.

Com LLC:
Runtime -> _decidir -> LLC.selecionar -> _agir.

A acao observar_sem_atuar e uma acao segura de nao atuacao, adicionada apenas para permitir que a politica tenha uma alternativa real sem criar shell ou executor arbitrario.

## Memoria estruturada

A memoria persistente continua sendo a mesma.

O contexto do ciclo seguinte passa a incluir:
- experiencia_anterior;
- avaliacao_anterior;
- acao_anterior;
- resultado_anterior.

O LLC nao cria uma segunda memoria.

## Governanca

O LLC nao:
- treina modelo;
- implanta modelo;
- modifica arquitetura;
- integra em main;
- cria autorizacao;
- executa shell;
- cria nova memoria;
- cria AE6.

Invariantes:

autorizacao_explicita = false
integracao_executada = false
stable_modificada = false
arquitetura_modificada = false
conhecimento_permanente = false
execucao_local = false
treinamento_automatico = false
implantacao_automatica = false
causalidade_ambiental_comprovada = false

## Proximo refinamento

Depois de provar influencia decisoria, o LLC precisara provar o elo completo:

aprendizado anterior
-> decisao influenciada
-> acao
-> resultado observado
-> ganho/perda
-> novo aprendizado

A primeira versao nao fecha esse elo ambiental completo; ela fecha apenas a prova de influencia da memoria estruturada na selecao.

## Estado

LLC.1.0.0 — implementacao inicial em branch separada do checkpoint M5.

M5 permanece congelado no branch feat/m5-habitat-nyxos.

Nenhuma rotina de boot, residencia adicional ou operacao comercial faz parte desta etapa.
