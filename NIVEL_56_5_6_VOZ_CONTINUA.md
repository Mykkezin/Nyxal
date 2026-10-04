# Nível 56.5.6 — Conversa por voz contínua

## Estado

**IMPLEMENTADO NA BRANCH DE DESENVOLVIMENTO**

Branch:
`feat/56-5-6-voz-conversa-continua`

## Objetivo

Fechar o caminho da conversa contextual na interface NyxOS e permitir conversação por voz contínua sem exigir um novo clique a cada turno.

Fluxo:

```
microfone
   ↓
VAD local no navegador
   ↓
segmento de fala
   ↓
POST /api/stt
   ↓
POST /api/chat + mesma sessão
   ↓
POST /api/tts
   ↓
reprodução
   ↓
retorno automático ao VAD
   ↓
...
```

## Mudanças

- uma única ativação inicia a conversa por voz;
- o microfone permanece autorizado durante a sessão;
- o navegador mantém a captura ativa enquanto a conversa está ouvindo;
- o VAD por RMS detecta a atividade e o fim da fala sem ser responsável por iniciar a gravação;
- cada turno é enviado como um segmento independente ao STT;
- o ID de sessão continua sendo reutilizado no `/api/chat`;
- durante o TTS o microfone é desativado para reduzir autoescuta/eco;
- após o TTS, a escuta volta automaticamente;
- um clique encerra explicitamente a conversa por voz;
- gravação fixa de 7 segundos foi removida;
- a captura começa imediatamente após a ativação da conversa;
- silêncio sem fala não é enviado ao STT;
- sem fala, o gravador é reciclado periodicamente para não acumular silêncio;
- limite de segurança de 12 segundos após o início da fala permanece;
- TTS Kokoro usa velocidade configurável, com padrão ligeiramente mais ágil;
- segmentos do Kokoro recebem micro-crossfade e fades curtos para reduzir cortes perceptíveis;
- fallback do navegador aguarda corretamente o término da fala.

## Limites

Esta etapa:

- não cria nova memória;
- não altera o contrato da memória 56.5.5;
- não promove conhecimento permanente;
- não executa comandos novos;
- não altera Git automaticamente;
- não modifica os gates N9/N10;
- não autoriza integração em stable/main.

## Validação

Teste estrutural/determinístico:

```bash
python3 teste_voz_continua_56_5_6.py
```

A validação cobre:

- presença do ciclo contínuo;
- remoção do temporizador fixo;
- reaproveitamento de sessão;
- retorno automático após TTS;
- cancelamento seguro da fala;
- VAD;
- configuração e suavização do Kokoro;
- sintaxe Python;
- sintaxe JavaScript quando Node está disponível.

## Teste manual

Com a API local ativa e a interface aberta:

1. clique uma vez no núcleo/globo;
2. fale normalmente;
3. aguarde a resposta da Nyxal;
4. fale novamente sem clicar no microfone;
5. clique uma vez somente para encerrar.

Teste contextual recomendado:

```
Meu nome é Mykke e estou construindo o NyxOS.
Qual é o sistema operacional que estou construindo?
```

A segunda fala deve utilizar a mesma sessão da conversa.

## Segurança operacional

O modo contínuo só existe depois de uma ativação explícita do usuário. Encerrar a conversa desliga a captura e interrompe fala em andamento.
