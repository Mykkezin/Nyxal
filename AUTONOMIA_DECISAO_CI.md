# Decisão autônoma governada para bloqueios de CI

## Objetivo

Este componente permite que a Nyxal escolha o próximo passo técnico a partir de evidências declaradas, sem repetir commits nem tratar qualquer estado `failure` como defeito de código. Ele é uma política determinística de escopo estreito; não substitui AE1–AE5, Nível 9/10 ou LLC, e não cria uma memória paralela.

## Política para o bloqueio de CI

A evidência histórica dos jobs de PR observados mostrou `conclusion=failure`, `runner_id=0`, `steps=[]` ou `steps=null` e logs indisponíveis (`BlobNotFound`). Esse sinal diz que os jobs não executaram os testes; não diz que os testes falharam. A decisão inicial, quando as validações locais ainda não têm resultado, é:

**`executar_validacao_local_sem_editar_codigo`**

O chamador deve fornecer evidências para:
- compilação de `nyxal_web_api.py` e `nixal_seguranca_http.py`;
- os testes de política HTTP em `teste_seguranca_api.py`;
- os 23 testes HTTP reais de `teste_api_security_auth.py`;
- os 8 cenários de `teste_decisao_autonoma_ci.py`;
- `teste_api_chat_sem_voz.py` e regressões principais.

Cada evidência deve identificar o SHA testado, comando, código de saída e logs. A política não finge executar esses comandos.

Se as verificações locais passarem e a CI continuar falhando antes de alocar runner em tentativas repetidas, a próxima decisão será `escalar_bloqueio_de_infraestrutura_ci`. Isso não afirma que billing ou cota é a causa. Se algum teste realmente executar e falhar, a decisão será `investigar_falha_real_de_validacao`. Se a CI executar os testes e tudo passar, a próxima fronteira será revisão humana.

## Evidência de execução e distinção entre pipeline e testes

O workflow usa `nixal_evidencia_ci.py`, separado da política de decisão, para produzir evidências a partir dos resultados reais de cada etapa. O documento registra dois campos independentes:

- `resultado_pipeline`: o estado geral do job e de todas as etapas;
- `resultado_testes`: o resultado das suítes de teste que realmente executaram (`passed`, `failed`, `not_run` ou `unknown`).

Falha de compilação ou de sintaxe do shell pode encerrar o pipeline e fazer com que as suítes seguintes sejam ignoradas. Nessa situação, o pipeline fica `failed`, mas os testes permanecem `not_run`; o decisor recomenda investigar a compilação em vez de afirmar que os testes falharam. Um erro em uma suíte que executou é registrado separadamente como falha real de teste. A contagem de tentativas anteriores de runner não é inferida pelo job atual.

## Interface

O chamador fornece JSON com `head_sha`, jobs observados, estado dos steps/logs, contagem de repetições pré-runner, se os testes foram realmente executados e estados locais (`not_run`, `passed`, `failed`, `unknown`).

    python nixal_decisao_autonoma_ci.py evidencia_ci.json

O módulo lê o JSON e imprime uma decisão estruturada com motivo, evidência, ID determinístico, passos seguintes, condição de bloqueio e invariantes. Não consulta GitHub, não executa comandos e não altera o repositório.

## Integração

A saída inclui um envelope de handoff ao ciclo AE/N9/LLC existente. A saída da execução CI é consumida pelo próprio workflow para escolher uma ação recomendada. A ligação automática com AE4/LLC dentro do ciclo residente continua dependendo do chamador e não deve ser considerada integrada enquanto não houver teste de ponta a ponta. Este componente não substitui nem duplica esses mecanismos.

## Limites de autoridade

- `merge_automatico`, `implantacao_automatica`, `integracao_executada`, `stable_modificada`, `arquitetura_modificada`, `conhecimento_permanente` e `treinamento_automatico` permanecem `false`.
- Não decide por conta própria executar código, mudar o repositório, desativar gates, publicar credenciais ou fazer merge/deploy.
- `steps=[]` ou `null` nunca é aceito como execução real de testes.
- Ausência de `runner_id` é evidência incompleta, não prova de falta de runner.
- Falha de infraestrutura e falha de código são classificações distintas.

## Validação

`teste_decisao_autonoma_ci.py` contém 11 cenários determinísticos, cobrindo pré-runner, escalada após validação local, falha de teste real, CI aprovada, steps vazias, entrada inválida, runner ausente, ID estável e separação entre falha de compilação, falha de suíte e falha de outra etapa do pipeline. `nixal_evidencia_ci.py` gera `resultado_testes` separadamente de `resultado_pipeline`; compilação falha com suítes ignoradas resulta em `testes_executados=false` e `resultado_testes=not_run`, não em falha de teste. O teste só conta como aprovado depois de execução real e código de saída zero.
