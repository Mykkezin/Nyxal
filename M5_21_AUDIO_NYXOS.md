# M5.21 — Camada de Áudio NyxOS

## Objetivo

Criar uma fronteira única para entrada e saída de áudio do NyxOS, preparada
para usar o dispositivo Bluetooth SOM-023.

## Dispositivo confirmado

No host do operador, o PipeWire expôs:

- saída: bluez_output.F4_75_FB_E9_74_8E.1;
- entrada: bluez_input.F4_75_FB_E9_74_8E.0;
- perfil: HFP/mSBC;
- áudio: mono, 16 kHz.

## Arquitetura

NyxOS → AudioNyxOS → PipeWire/PulseAudio → SOM-023

A camada:
- descobre sinks e sources;
- seleciona o dispositivo preferencial;
- identifica capacidade bidirecional;
- permite selecionar sink/source padrão;
- não inicia voz automaticamente;
- não implementa TTS ou STT nesta etapa.

## Governança

A camada de áudio é I/O de interface. Ela não concede autorização de atuação
física, não altera arquitetura e não promove conhecimento.

As operações externas ficam atrás de executor injetável para permitir testes
sem depender do host.

## Próximo passo

Adicionar TTS e captura STT atrás dessa fronteira, mantendo a voz desligada
por padrão até a validação E2E.
