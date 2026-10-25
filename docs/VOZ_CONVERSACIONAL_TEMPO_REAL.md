# Voz conversacional em tempo real — avaliação experimental

## Objetivo

Evoluir o orbe da Nyxal de um ciclo sequencial de gravação → transcrição → geração completa do áudio → reprodução para uma conversa de voz contínua, com resposta local, voz feminina, reprodução assíncrona e interrupção quando o usuário começa a falar novamente.

O protótipo é experimental. Não substitui o núcleo conversacional, a memória ou a API existentes, e não ativa captura automática por conta própria no sistema estável.

## Diagnóstico atual

- A API já oferece `POST /api/stt` com Faster-Whisper local e `POST /api/tts` com Kokoro local.
- O endpoint de TTS usa `NYXAL_KOKORO_VOICE`, cujo padrão documentado é `pf_dora` (voz feminina pt-BR).
- O orbe atual instalado localmente usa uma rotina de áudio própria e `espeak-ng`; isso explica a voz diferente. A geração/reprodução sequencial bloqueante também não oferece por si só barge-in.
- `POST /api/chat` aceita `mensagem` e `sessao`; o protótipo reutiliza esse contrato para que capacidades e memória conversacional do núcleo Nyxal continuem sendo a autoridade. Não cria um segundo histórico de chat.

## Componentes avaliados

| Projeto | Papel na avaliação | Decisão |
| --- | --- | --- |
| [Pipecat](https://github.com/pipecat-ai/pipecat) | Pipeline de áudio em tempo real, interrupções e serviços locais | Protótipo opcional escolhido |
| [Kokoro](https://github.com/hexgrad/kokoro) | Voz local e streaming TTS | Manter; protótipo usa integração Kokoro ONNX do Pipecat para streaming |
| [Silero VAD](https://github.com/snakers4/silero-vad) | Detecção de fala | Usar pelo processador VAD do Pipecat |
| [LiveKit Agents](https://github.com/livekit/agents) | Alternativa com turn detection e interrupções | Avaliado, mas não escolhido na primeira etapa por adicionar uma arquitetura mais orientada a sessões/WebRTC |

O Pipecat é distribuído sob BSD-2-Clause. A integração referencia a biblioteca instalada e não copia o código-fonte do projeto para Nyxal.

## Arquitetura experimental

```text
Microfone / PyAudio
  → Silero VAD
  → evento de nova fala / InterruptionFrame
  → Faster-Whisper local (pt)
  → POST 127.0.0.1:8010/api/chat com ID de sessão estável
  → Kokoro ONNX local, voice pf_dora, áudio em frames
  → saída de áudio local
```

O processador de interrupção também incrementa um identificador de geração. Se uma nova fala começa enquanto a API ainda está produzindo uma resposta, o resultado antigo é descartado e não deve ser reproduzido. O processamento HTTP é assíncrono; o transporte de áudio do Pipecat escreve no dispositivo por um executor dedicado.

## Dependências e armazenamento

- Instalar somente no ambiente virtual isolado em `~/.local/share/nyxal-voice-pipecat/venv` através de `deploy/voice/instalar_pipecat_experimental.sh`.
- Não adicionar essas dependências ao ambiente principal `.venv` até passar os testes.
- Pipecat baixa, no primeiro uso, seus arquivos de modelo Kokoro para `~/.cache/pipecat/kokoro-onnx`. Eles não entram no repositório, nem são incluídos em commits ou releases.
- A captura, transcrição, geração de resposta e TTS do protótipo são locais. A primeira instalação pode precisar baixar pacotes e modelos.
- Nenhuma unidade systemd é instalada, ativada ou substituída pelo instalador experimental.

## Como testar manualmente

Faça os testes em branch experimental e não rode dois ouvintes de microfone em paralelo.

1. Confirme que a API existente está ativa:

   ```bash
   systemctl --user is-active nyxal-api.service
   curl -fsS http://127.0.0.1:8010/health
   ```

2. Instale o ambiente separado:

   ```bash
   cd ~/Nyxal
   bash deploy/voice/instalar_pipecat_experimental.sh
   ```

3. Para evitar que o ouvinte atual concorra pelo microfone, pare temporariamente o serviço de desktop existente (isso também fecha o orbe atual, sem desativá-lo):

   ```bash
   systemctl --user stop nyxal-desktop.service
   ```

4. Inicie o protótipo:

   ```bash
   ~/.local/share/nyxal-voice-pipecat/venv/bin/python deploy/voice/nyxal_pipecat_agent.py
   ```

   O arquivo carrega configurações de `~/.config/nyxal/nyxal.env`. Para selecionar outra voz compatível, use `NYXAL_KOKORO_VOICE`; o padrão é `pf_dora`. Para alterar o modelo STT, use `NYXAL_PIPECAT_WHISPER_MODEL` ou o já existente `NYXAL_WHISPER_MODEL`.

5. Fale uma pergunta, deixe a Nyxal responder e interrompa a resposta falando novamente. Faça ao menos três turnos seguidos para verificar que a sessão é mantida.

6. Ao encerrar com Ctrl+C, volte ao desktop atual:

   ```bash
   systemctl --user start nyxal-desktop.service
   ```

Recomenda-se usar fones durante a avaliação, porque o protótipo não adiciona cancelamento acústico de eco: o microfone pode captar a voz reproduzida nos alto-falantes e iniciar uma interrupção falsa.

## Critérios de aceite antes de qualquer ativação automática

- Voz ouvida é Kokoro `pf_dora`, sem fallback para `espeak-ng`.
- O orbe/UI e o desktop permanecem responsivos durante a fala.
- Ao começar a falar sobre a resposta da Nyxal, o áudio em andamento é interrompido e uma resposta antiga não é reproduzida depois.
- Três ou mais turnos são encaminhados pelo mesmo ID de sessão ao `/api/chat`.
- Falha/timeout da API não encerra o pipeline de áudio.
- Transcrições e respostas não são gravadas nos logs do protótipo.
- Consumo de CPU/RAM, latência até a primeira fala, falsa interrupção e perda de transcrições são medidos na máquina de destino.
- A integração não muda a configuração estável nem habilita o serviço automaticamente.

## Limitações conhecidas

- O núcleo Nyxal continua produzindo a resposta do chat antes da síntese de voz; o TTS é transmitido em frames, mas a geração textual do núcleo ainda pode determinar a maior parte da latência.
- Sem cancelamento acústico de eco, os alto-falantes podem ser captados pelo microfone. Testar primeiro com fones.
- `pf_dora` precisa existir no pacote de vozes Kokoro ONNX baixado. Se a versão do modelo não disponibilizar esse ID, a inicialização deve falhar visivelmente em vez de aceitar silenciosamente uma voz masculina.
- O protótipo não instala um serviço systemd nem substitui a interface nativa. Isso só deve ser integrado depois de medir o funcionamento em hardware real.

## Referências primárias

- [Pipecat — repositório e arquitetura](https://github.com/pipecat-ai/pipecat)
- [Pipecat — interrupções](https://docs.pipecat.ai/pipecat/fundamentals/interruptions.md)
- [Pipecat — áudio local](https://github.com/pipecat-ai/pipecat/blob/main/src/pipecat/transports/local/audio.py)
- [Pipecat — Kokoro TTS local](https://github.com/pipecat-ai/pipecat/blob/main/src/pipecat/services/kokoro/tts.py)
- [Pipecat — Whisper local](https://github.com/pipecat-ai/pipecat/blob/main/src/pipecat/services/whisper/stt.py)
- [LiveKit Agents — repositório alternativo](https://github.com/livekit/agents)
- [Kokoro — modelo original](https://github.com/hexgrad/kokoro)
- [Silero VAD — modelo original](https://github.com/snakers4/silero-vad)
