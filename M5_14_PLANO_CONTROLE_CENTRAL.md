# M5.14 — Plano Central de Controle

## Objetivo

Unificar observação, seleção semântica e passagem para atuação controlada em uma superfície principal, sem criar um novo executor ou uma nova autoridade.

## Superfície

Operações estruturadas:

- `observar`;
- `selecionar_capacidade`;
- `atuar_host`.

A superfície rejeita linguagem natural como operação. Texto pode existir somente como dado de necessidade dentro da operação semântica.

## Separação preservada

```
observação
   ↓
plano central
   ├── seleção semântica → agente
   └── atuação → Gateway M5.10
                         ↓
                    executor registrado
```

O plano central não executa shell, não chama executores de host diretamente e não concede autorização de evolução.

## M5.11 e M5.12 integrados

O plano central pode receber o Gateway que expõe as ações controladas de processos/aplicativos e a fisiologia que representa o estado operacional.

## Governança

Os invariantes permanecem:

- autorização explícita de evolução: `false`;
- integração executada: `false`;
- arquitetura modificada: `false`;
- conhecimento permanente: `false`;
- executor próprio: `false`;
- shell arbitrário: `false`.

## Critério de conclusão

M5.14 será fechado quando o CI confirmar observação, seleção, roteamento para o gateway e preservação das fronteiras de execução.