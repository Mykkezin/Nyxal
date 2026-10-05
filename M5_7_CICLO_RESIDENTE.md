# M5.7 — Ciclo operacional residente

## Objetivo

Manter o Runtime capaz de executar ciclos de forma contínua, interrompível e observável, criando a residência operacional do NyxOS sobre Linux.

Fluxo:

```
habitat observado
      ↓
Runtime
      ↓
ciclo operacional
      ↓
resultado
      ↓
persistência / Delta
      ↓
novo ciclo
```

## Garantias

- residência é opt-in e explícita;
- interrupção é possível;
- ciclos são delegados ao Runtime existente;
- erros podem interromper a residência;
- nenhum comando externo é executado pelo controlador;
- nenhuma evolução remota é disparada automaticamente;
- `auto_evolution_habilitada = false`;
- nenhuma autorização de integração é criada pelo controlador;
- stable permanece fora do processo;
- arquitetura não é modificada.

## Reentrada

Uma instância pode executar mais de uma sessão residente. A contagem de ciclos totais é separada da quantidade de ciclos da sessão atual.

## Critério de conclusão

M5.7 é implementado quando:

1. o controlador executa ciclos de forma contínua ou limitada;
2. a residência pode ser interrompida;
3. o último resultado permanece observável;
4. a persistência operacional é atualizada;
5. falhas obedecem à política de parada;
6. a residência não concede auto-evolution nem autorização de integração.
