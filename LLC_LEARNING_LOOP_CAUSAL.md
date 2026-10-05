# LLC — Learning Loop Causal

## Estado atual: LLC.2 validado

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

## LLC.2 — Feedback operacional e fechamento da transicao

A segunda etapa fecha o encadeamento dentro do ciclo:

aprendizado anterior
-> decisao influenciada
-> acao
-> resultado observado
-> ganho/perda operacional
-> novo aprendizado

O ganho/perda desta etapa e deliberadamente operacional:
- sucesso conjunto da acao e do resultado observado: +1.0;
- observacao sem atuacao: 0.0;
- falha da acao ou do resultado: -1.0.

Esse valor representa a consequencia observada da operacao registrada. Ele nao representa
melhoria ambiental, retorno economico ou causalidade sobre o mundo.

Depois que o aprendizado persistente e registrado, o LLC fecha uma transicao auditavel com:
- aprendizado_anterior_id;
- decisao e influencia_decisoria_comprovada;
- acao;
- resultado;
- feedback_operacional;
- avaliacao;
- aprendizado_novo_id.

Assim, o elo estrutural do LLC esta fechado para a camada operacional. A prova de
causalidade ambiental permanece pendente de uma etapa posterior com metricas externas
e contrafactuais apropriados.

## Validacao LLC.2

O pipeline dedicado confirmou:
- compilacao do LLC e dependencias: PASSOU;
- teste de influencia decisoria: PASSOU;
- teste de ganho/perda operacional: PASSOU;
- teste de fechamento com aprendizado anterior e novo aprendizado: PASSOU;
- invariantes de governanca: PASSOU.

## Estado

LLC.2.0.0 — implementacao e validacao da influencia decisoria + feedback operacional
em branch separada do checkpoint M5.


M5 permanece congelado no branch feat/m5-habitat-nyxos.

Nenhuma rotina de boot, residencia adicional ou operacao comercial faz parte desta etapa.
