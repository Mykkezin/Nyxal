# Relatório de implementação e auditoria da voz local

Data: 2026-11-06 · Branch: `feat/palmas-openjarvis` · Commit-base: `1f43e6e`

## Auditoria do host

- CPU: AMD Ryzen 7 5700, 8 núcleos / 16 threads.
- RAM: 15 GiB totais, 9,6 GiB disponíveis no momento da leitura; swap de 2 GiB.
- GPU: AMD Radeon Navi 33, PCI ID `1002:7480`, exposta pelo kernel como família RX 7700S/7600. Não há `nvidia-smi`; este host usa AMD.
- Disco de `/home/nyxal`: 109 GiB totais, 29 GiB livres (73% ocupado).
- Ollama: serviço systemd de sistema ativo; modelos `qwen2:7b` e `nomic-embed-text:latest`. `qwen2:7b` tem arquitetura Qwen2, 7,6 bilhões de parâmetros, quantização Q4_0 e contexto de 32.768 tokens. O diálogo Nyxal já usa esse modelo. Foi mantido como modelo de conversa: ele está instalado e não se adiciona uma segunda camada de Runtime. Com 9,6 GiB livres, o uso em CPU é plausível; memória de GPU efetivamente usada e latência de geração ainda não foram medidas.
- Voz local: ambiente isolado instalado com Pipecat 1.14.0, faster-whisper 1.2.1, kokoro-onnx 0.6.1, onnxruntime 1.31.0 e PyAudio 0.2.14. Pesos Kokoro ONNX e pacote de vozes estão no cache local; os caches Faster-Whisper `base` e `tiny` existem. O padrão permanece `base`, idioma português, TTS Kokoro `pf_dora`.
- Áudio: captura analógica ALC897 disponível; saída analógica ALC897 e saídas HDMI disponíveis. PipeWire 1.0.5 com PulseAudio compatível ativo. Entrada padrão `alsa_input.pci-0000_30_00.6.analog-stereo`; saída padrão `alsa_output.pci-0000_30_00.6.analog-stereo`.
- Serviços Nyxal: `systemctl --user show nyxal-api.service` retornou `LoadState=not-found`; `GET http://127.0.0.1:8010/health` recusou conexão. A unidade pedida não existe neste usuário, portanto não foi criada nem substituída. A API precisa estar ativa para testar conversa real. Nenhum serviço foi iniciado, parado ou ativado durante esta implementação.

## Mudanças

- `deploy/voice/nyxal_clap_wake.py`: detector de duas palmas (transientes acima do limiar, separadas por 120–950 ms) e reconhecimento local dos comandos de repouso, incluindo variantes de transcrição `Nixau`/`Nixal`.
- `deploy/voice/nyxal_pipecat_agent.py`: estado inicial em repouso, gate local de áudio, limiar ajustável por `NYXAL_CLAP_THRESHOLD`, variantes fonéticas nas hotwords e comando de repouso antes da API. A conversa continua passando pelo `/api/chat` e sua sessão Nyxal; o módulo não cria memória ou Runtime próprios.
- `deploy/systemd/nyxal-voice.service`: unidade de usuário opcional, preflight da API em loopback, reinício em falha e limite de cinco partidas em cinco minutos. Não instalada nem habilitada.
- `docs/VOZ_CONVERSACIONAL_TEMPO_REAL.md`: operação, rollback e roteiro manual.

## Evidências executadas

- Quatro testes determinísticos do detector/comandos passaram. Eles não acessam microfone.
- Doze verificações de contrato Pipecat passaram.
- `py_compile`, `bash -n` do instalador e `git diff --check` passaram.
- `systemd-analyze verify` aceitou a unidade de voz; exibiu avisos preexistentes de `/etc/systemd/system/deepcool.service` e um nome de usuário-placeholder, sem apontar erro em `nyxal-voice.service`.
- Captura ALSA real de 2 s entregou 64.000 bytes / 32.000 amostras (RMS 0,00556, pico 0,02960), sem gravar o áudio em arquivo. Isso confirma abertura e fluxo do dispositivo; não valida reconhecimento de fala nem palmas.
- Kokoro gerou 47.616 amostras, 24 kHz, para texto fixo em `pf_dora`/pt-BR e a amostra foi enviada à saída PulseAudio padrão. Também foi reproduzido um tom de 660 Hz por 350 ms. A confirmação de que a fala e o tom foram audíveis depende de uma pessoa no computador.
- Faster-Whisper `base`/CPU int8 transcreveu localmente a amostra sintética de pt-BR como “Teste de voz local da Nixau.”. O texto não bateu literalmente com “Nyxal”, apesar da configuração do agente incluir a hotword `Nyxal`; a taxa de acerto com fala humana e palmas ainda não foi medida.
- Foi incluída normalização de `Nixau`/`Nixal`/`Nicsal` no comando de repouso, novas hotwords e um limiar de palmas configurável; a transcrição sintética ainda não foi reexecutada usando o novo prompt/hotwords do agente.
- Benchmark concorrente curto (Ollama `qwen2:7b`, Whisper base int8 e Kokoro `pf_dora`): janela de 11,02 s; Ollama 10,87 s (16 tokens medidos); Whisper 1,70 s para 2,41 s de áudio; Kokoro 2,41 s de áudio; RSS máximo do cgroup Ollama 4,80 GiB; CPU máxima do cgroup 150,7% de um núcleo; mínimo de 8,12 GiB disponíveis. Após o teste, `ollama ps` ficou vazio, o modelo foi descarregado e a RAM disponível marcou 9,0 GiB (swap usado 2,3 MiB). É uma amostra curta e não representa estabilidade prolongada nem utilização de VRAM.
- Uma primeira coleta concorrente de CPU/RSS varrendo `/proc` foi interrompida por overhead excessivo do próprio monitor. A execução final usou os contadores leves do cgroup Ollama e terminou normalmente; nenhum dado Nyxal foi acessado.
- `deploy/voice/verificar_api_nyxal.py` não foi executado: o script envia duas mensagens reais para `/api/chat` e persiste a sessão na memória conversacional configurada pela unidade API. Como essa unidade não existe e a instrução exige preservar memória, não iniciei a API por um caminho alternativo nem executei esse smoke test.
- Sem API não foi feita chamada real de chat, sessão contínua ou teste end-to-end. A unidade de voz não foi instalada/ativada e o serviço não pode ser declarado operacional.

## Aceite físico ainda necessário

1. Inicie a API Nyxal pelo mecanismo que já usa e confirme `curl -fsS http://127.0.0.1:8010/health`.
2. Inicie manualmente o agente pelo comando da seção “Como testar manualmente”. Use fones primeiro.
3. Em silêncio, bata palmas duas vezes com cerca de meio segundo entre elas. Confirme a mensagem “duas palmas detectadas” no terminal; depois faça três perguntas em português e confirme que a Nyxal responde em `pf_dora`.
4. Durante uma resposta, comece a falar outra pergunta. Confirme que o áudio anterior para e que a resposta atrasada não volta a tocar.
5. Diga “Nyxal, pode descansar”. Confirme a resposta de repouso; fale sem bater palmas e confirme que não há transcrição/resposta. Bata palmas duas vezes e confirme que a escuta volta.
6. Confirme que o tom curto deste relatório foi ouvido. Se a saída selecionada ou o microfone forem outros, selecione-os no PipeWire antes do teste.

Até esses passos serem aprovados, não habilite a unidade systemd. Para rollback de código, descarte esta branch; backup datado dos arquivos modificados está em `/tmp/nyxal-voice-backup-20261106-2336`.
