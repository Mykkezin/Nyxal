# Nível 56.5.5 — Conversa contextual

## Estado

**IMPLEMENTADO NA BRANCH DE DESENVOLVIMENTO**

Branch:
`feat/56-5-5-conversa-contextual-ci3`

Pull Request:
`#16 — 56.5.5: conversa contextual — validação final v3`

## Objetivo

Transformar a fronteira conversacional já existente em uma conversa contextual enquanto o processo da Nyxal estiver em execução.

Fluxo:

```
usuário
  ↓
interface 56.5.1
  ↓
transporte 56.5.2
  ↓
sessão 56.5.3 / integração 56.5.4
  ↓
núcleo conversacional
  ├── capacidade executável
  └── diálogo Qwen
        ↓
memória conversacional volátil
  ↓
resposta
```

## O que mudou

- contexto recente por sessão;
- janela máxima configurável de mensagens;
- contexto separado por sessão;
- diálogo livre pelo Qwen quando nenhuma capacidade atende à mensagem;
- capacidade executável continua passando pelo `AgenteNixalQwen`;
- frontend envia e reaproveita automaticamente o ID da sessão;
- reinício do processo elimina o contexto conversacional volátil.

## Limites

A memória 56.5.5:

- não é memória de conhecimento;
- não promove fatos para `conhecimento_base.json`;
- não altera a arquitetura;
- não executa comandos;
- não modifica Git;
- não substitui os gates do Nível 9;
- não autoriza integração em stable/main.

## Execução local

No diretório do projeto:

```bash
python3 nyxal_web_api.py
```

Por padrão, a API escuta em:

```
http://127.0.0.1:8010
```

A interface web já está preparada para usar esse endereço.

### Teste de saúde

```bash
curl -s http://127.0.0.1:8010/health
```

### Primeira mensagem

```bash
curl -s -X POST http://127.0.0.1:8010/api/chat \
  -H "Content-Type: application/json" \
  -d '{"mensagem":"Olá, Nyxal."}'
```

A resposta inclui `sessao`.

### Continuação da conversa

Use o mesmo valor de `sessao`:

```bash
curl -s -X POST http://127.0.0.1:8010/api/chat \
  -H "Content-Type: application/json" \
  -d '{"mensagem":"Você lembra do que acabamos de conversar?","sessao":"SESSAO_AQUI"}'
```

## Modo terminal

Para conversar sem abrir a interface web:

```bash
python3 conversar_nyxal.py
```

A sessão é criada automaticamente. Digite `sair` para encerrar.

## Voz

A API mantém:

```
POST /api/stt
POST /api/tts
```

Assim, o fluxo de voz do frontend pode continuar usando STT → chat contextual → TTS.

## Validação

Suíte determinística:

```bash
python3 teste_contexto_conversacional_56_5_5.py
```

O teste usa dublês locais e não precisa consultar um modelo Qwen real.

## Telemetria da sessão

Quando uma mensagem é processada com uma sessão ativa, a resposta integrada pode indicar:

- `mensagem_armazenada: true` quando a mensagem do usuário e a resposta da Nyxal foram registradas no contexto volátil da sessão;
- `memoria_conversacional: true` quando o processamento utilizou ou registrou memória conversacional;
- `conhecimento_permanente: false` para este fluxo;
- `arquitetura_modificada: false`.

Esses campos descrevem o estado operacional da conversa e não transformam o contexto volátil em conhecimento permanente.

## Relação com Nível 10

Esta microetapa é uma extensão operacional da conversa local. Ela não concede autorização de integração e não altera o significado dos estados de aprovação do Nível 10.

O PR #11 permanece Draft e separado de stable/main. A 56.5.5 permanece isolada no PR #16.
