# M5.13 — Fisiologia Operacional

## Objetivo

Formalizar heartbeat, regularidade do ciclo, presença operacional e estados térmicos derivados de evidências observadas pelo corpo.

## Heartbeat

O heartbeat compara o intervalo real entre ciclos com o intervalo esperado do residente.

- `inicializando`: não existe amostra anterior persistida;
- `regular`: ciclo dentro do esperado + tolerância de 2 segundos;
- `atrasado`: intervalo acima desse limite.

## Fisiologia

Os estados são derivados, não inventados por linguagem natural:

- `normal`;
- `estresse_termico`;
- `febre`;
- `recuperacao`;
- `sem_sinal`;
- `inicializando` antes da primeira evidência.

## Febre

`febre` exige três observações consecutivas classificadas como `muito_quente`. Uma única leitura alta não cria esse estado.

Após febre, três observações `normal` ou `fria` encerram a recuperação e retornam ao estado normal.

## Persistência

O histórico fisiológico é persistido e limitado a 20 registros. Após reinício, o componente reconstrói seu estado básico a partir desse histórico.

## Delta

Transições fisiológicas observadas podem gerar eventos Delta. Esses eventos são observacionais e não concedem autorização para atuação, evolução ou integração.

## Integração residente

O launcher Linux instancia a fisiologia usando o intervalo real do residente e o registrador Delta já existente. Cada ciclo recebe apenas um resumo compacto da fisiologia.

## Segurança

M5.13 não habilita:

- controle automático de ventoinhas;
- atuação física;
- alteração da arquitetura;
- autorização de evolução;
- integração em `main`.

## Critério de conclusão

M5.13 será fechado quando o CI confirmar heartbeat, febre, recuperação, persistência limitada e integração ao ciclo residente sem regressão.