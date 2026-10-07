# M5.24 — Voz supervisionada

## Objetivo

Fechar a fronteira operacional entre `VozNyxOS` e os adaptadores reais STT/TTS por meio de uma operação explicitamente solicitada e auditável, sem habilitar voz automática, captura contínua ou reprodução física automática.

## Problema

M5.23 integrou os adaptadores `faster-whisper` e `Kokoro` ao contrato de `VozNyxOS` e validou a integração determinística por injeção. O host real também demonstrou STT e TTS funcionais fora do ciclo automático.

O próximo marco deve validar uma operação composta no próprio contrato de `VozNyxOS`, mantendo os motores externos na borda.

## Escopo

Incluído:

- operação supervisionada de transcrição;
- operação supervisionada de síntese;
- registro estruturado do resultado;
- preservação do estado `voz_habilitada=False`;
- preservação de `execucao_automatica=False`;
- testes determinísticos com adaptadores injetados;
- teste negativo para ausência de STT/TTS;
- documentação do contrato.

Não incluído:

- ativação automática de voz;
- escuta contínua;
- wake word;
- reprodução física automática;
- envio automático de áudio ao Runtime;
- concessão de autoridade ao gateway;
- alteração de `main` fora do fluxo normal de PR;
- criação de M6 ou AE6.

## Contrato proposto

A operação supervisionada deverá aceitar uma entrada de áudio já disponível e produzir um registro estruturado contendo, quando aplicável:

- sucesso;
- estado;
- texto transcrito;
- arquivo de áudio sintetizado;
- origem;
- indicação de execução automática;
- indicação de voz habilitada.

Falhas de dependência devem permanecer explícitas e não devem ser convertidas em sucesso.

## Autoridade

Autoridade concedida:

- chamar explicitamente STT/TTS injetados;
- produzir artefatos de áudio em local permitido pelo adaptador;
- registrar o resultado da operação.

Autoridade proibida:

- iniciar captura espontaneamente;
- iniciar reprodução física espontaneamente;
- alterar hardware;
- alterar `main`;
- integrar conhecimento permanente;
- modificar arquitetura fora do escopo aprovado.

## Reversibilidade

A mudança deve ser local à camada `VozNyxOS` e seus testes. Remover o novo método e seus testes deve restaurar o comportamento anterior sem migração de estado.

## Validação

O marco só será considerado concluído quando:

1. testes determinísticos do novo contrato passarem;
2. regressão M5/LLC continuar passando;
3. os invariantes de voz automática permanecerem falsos;
4. nenhum caminho físico automático for introduzido;
5. o PR for revisado e integrado em `main`.

## Critério de saída

M5.24 será concluído se a operação supervisionada puder executar o caminho:

```
arquivo de áudio existente
→ STT explícito
→ texto
→ TTS explícito
→ arquivo de áudio
→ registro auditável
```

sem transformar a operação em voz automática ou em ação física.

## Governança

M5.24 não concede autoridade de evolução. Resultados positivos são evidência de funcionamento do contrato, não autorização para automatização posterior.
