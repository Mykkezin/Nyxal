# M5.11 — Controle de Processos e Aplicativos

## Objetivo

Adicionar as primeiras ações concretas de atuação sobre processos e aplicativos sem criar uma segunda rota de execução. Toda atuação atravessa o Gateway M5.10.

## Ações implementadas

### iniciar_aplicativo_conhecido

- recebe somente o identificador de aplicativo;
- aceita apenas aplicativos presentes no mapa fixo;
- não recebe caminho arbitrário;
- não recebe comando ou argumentos arbitrários;
- usa lançamento sem shell;
- retorna PID e executável utilizado.

Aplicativos iniciais:

- `terminal`;
- `navegador`.

### encerrar_processo_usuario

- recebe somente PID inteiro;
- rejeita PID protegido;
- rejeita o próprio processo da Nyxal;
- exige que o processo alvo pertença ao usuário atual;
- envia somente SIGTERM;
- não usa SIGKILL.

## Governança

Ambas as ações:

- possuem contrato declarativo;
- exigem autorização explícita no Gateway M5.10;
- são observáveis;
- podem gerar Delta;
- não concedem autoridade de evolução;
- não modificam arquitetura;
- não integram `main`;
- não são registradas como capacidades abertas ao Qwen neste marco.

Essa última regra é deliberada: adicionar uma ação ao gerenciador semântico atual faria o Qwen poder executá-la diretamente e criaria um caminho que contornaria o Gateway.

## Arquitetura

```
ordem/intent
   ↓
seleção estruturada
   ↓
Gateway M5.10
   ↓
contrato + allowlist + política
   ↓
Controle de processos/aplicativos
   ↓
OS
   ↓
resultado
   ↓
Delta / observabilidade
```

## Validação

O teste M5.11 cobre:

1. contexto e invariantes do gateway;
2. bloqueio sem autorização;
3. aplicativo inexistente no allowlist;
4. dry-run;
5. tipo inválido de PID;
6. proteção contra autoencerramento;
7. atuação real contra um processo filho temporário;
8. uso de SIGTERM;
9. ausência de shell arbitrário;
10. registro Delta.

## Critério de conclusão

M5.11 será fechado quando o CI confirmar o teste específico junto da regressão completa do Habitat.

M5.12 permanece como próxima etapa: corpo térmico e ventilação.