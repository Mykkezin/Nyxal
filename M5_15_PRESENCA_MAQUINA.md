# M5.15 — Presença de Máquina

## Objetivo

Fechar a cadeia de presença persistente do NyxOS usando a residência Linux já validada, sem criar um segundo daemon.

## Modelo

```
boot/login
   ↓
systemd --user / nyxos.target
   ↓
nyxal-api + nyxos-residente
   ↓
heartbeat
   ↓
marcador de presença
   ↓
interface / API
```

O M5.15 formaliza a presença como estado operacional persistente. A infraestrutura de residência continua sendo a estabelecida no M5.9.

## Marcador

`presenca_maquina_nyxos.json` mantém um único estado compacto com:

- startup atual;
- instante de inicialização;
- último heartbeat;
- encerramento conhecido, quando houver;
- motivo do encerramento;
- indicação de retomada;
- presença das unidades systemd esperadas.

Não existe histórico de ciclos nesse arquivo.

## Retomada

Quando uma nova instância encontra o marcador anterior em estado `ativo` ou `heartbeat`, registra `retomada_apos_reinicio`.

Um encerramento controlado grava `encerrado`, permitindo distinguir uma próxima inicialização normal de uma retomada após interrupção.

## Integração

O `nyxos-residente.service` continua sendo o único processo do ciclo. O launcher instancia `PresencaMaquinaNixOS`, e o `CicloResidenteNixOS` atualiza o heartbeat sem criar outro loop residente.

A API pública expõe o contexto de presença para a interface e para observabilidade.

## Voz e interface

Os canais conversacional e de voz já existentes permanecem os canais de interação. M5.15 não duplica esses mecanismos; apenas os conecta ao conceito formal de presença da máquina.

## Segurança

M5.15 não concede:

- shell arbitrário;
- execução extra de processos;
- autoridade de evolução;
- alteração de arquitetura;
- integração em `main`.

## Persistência e memória

O marcador é sobrescrito atomicamente a cada heartbeat. Não acumula resultados, não cria lista histórica e não reintroduz o problema de crescimento observado no ciclo residente antigo.

## Critério de conclusão

M5.15 será fechado quando o CI comprovar marcador persistente, heartbeat, retomada após estado ativo, observação das unidades systemd e integração ao residente sem regressão.