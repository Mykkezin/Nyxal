# M5.22 — Voz NyxOS

## Objetivo

Criar a ponte entre o áudio bidirecional do NyxOS e motores externos de STT (fala → texto) e TTS (texto → fala).

## Fluxo

SOM-023 → AudioNyxOS → captura → STT → Nyxal → TTS → AudioNyxOS → SOM-023

## Governança

- voz automática permanece desabilitada;
- motores STT/TTS são injetados explicitamente;
- nenhum comando de sistema é executado pelo núcleo M5.22;
- nenhuma autorização de atuação física é criada;
- nenhuma alteração arquitetural automática é permitida.

## Limite desta etapa

M5.22 valida a interface e o encadeamento lógico. A escolha e instalação de um motor STT/TTS real no host serão validadas separadamente no ambiente físico do NyxOS.

O SOM-023 é tratado como endpoint de áudio; isso não significa acesso à voz proprietária do assistente Alexa.
