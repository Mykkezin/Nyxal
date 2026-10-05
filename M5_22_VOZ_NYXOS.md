# M5.22 — Voz NyxOS

## Objetivo

Criar a ponte entre o áudio bidirecional do NyxOS e motores externos de STT (fala → texto) e TTS (texto → fala).

## Fluxo

SOM-023 → AudioNyxOS → captura → STT → Nyxal → TTS → AudioNyxOS → SOM-023

## Estado físico validado

No host Nyxal, o SOM-023 foi validado fisicamente em A2DP/SBC:

- sink PipeWire `bluez_output.F4_75_FB_E9_74_8E.1`;
- 2 canais, 48 kHz;
- `pw-play` reproduziu o WAV de teste;
- o áudio foi ouvido fisicamente no dispositivo.

O modo HFP/mSBC e a captura pelo microfone ainda permanecem pendentes de validação física.

## Reprodução

`AudioNyxOS.reproduzir()` agora possui uma execução física explícita e reversível por chamada:

- `executar_fisico=False` por padrão;
- com `False`, somente prepara a saída;
- com `True`, chama o adaptador injetado para executar `pw-play --target <sink> <arquivo>`;
- nenhum processo de reprodução é iniciado automaticamente pelo residente.

A execução continua atrás de um executor injetável para preservar testes determinísticos.

## Governança

- voz automática permanece desabilitada;
- motores STT/TTS são injetados explicitamente;
- reprodução física exige `executar_fisico=True` na chamada;
- nenhuma autorização de atuação física do Gateway é criada;
- nenhuma alteração arquitetural automática é permitida.

## Limite desta etapa

M5.22 valida a interface de voz e a ponte física explícita de saída. A escolha e instalação de um motor STT/TTS real no host serão validadas separadamente.

O SOM-023 é tratado como endpoint de áudio; isso não significa acesso à voz proprietária do assistente Alexa.